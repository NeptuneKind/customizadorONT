from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSequentialAnimationGroup,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

DURATION_FAST = 120
DURATION_STANDARD = 160
DURATION_SLOW = 200

# Helper para mantener referencias a animaciones activas
def _get_animation_store(owner: QObject) -> dict[str, QAbstractAnimation]:
    store = getattr(owner, "_ui_animations", None)
    if store is None:
        store = {}
        setattr(owner, "_ui_animations", store)
    return store

# Helper para trackear animaciones por clave y detener animaciones previas si es necesario
def _track_animation(owner: QObject, key: str, animation: QAbstractAnimation) -> None:
    store = _get_animation_store(owner)
    previous = store.get(key)
    if previous is not None and previous.state() != QAbstractAnimation.Stopped:
        previous.stop()
    store[key] = animation

# Helper para activar los ancestros de un widget y actualizar su geometría
def _activate_ancestors(widget: QWidget) -> None:
    widget.updateGeometry()

    parent = widget.parentWidget()
    while parent is not None:
        parent.updateGeometry()
        layout = parent.layout()
        if layout is not None:
            layout.activate()
        parent = parent.parentWidget()

# Método para asegurar que un widget tenga un efecto de opacidad
def ensure_opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
    effect = widget.graphicsEffect()
    if isinstance(effect, QGraphicsOpacityEffect):
        return effect

    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(1.0)
    widget.setGraphicsEffect(effect)
    return effect

# Animación de opacidad
def animate_opacity(
    widget: QWidget,
    start_value: float,
    end_value: float,
    duration: int = DURATION_FAST,
    key: str = "opacity",
) -> QPropertyAnimation:
    effect = ensure_opacity_effect(widget)
    effect.setOpacity(float(start_value))

    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setEasingCurve(QEasingCurve.InOutCubic)
    animation.setStartValue(float(start_value))
    animation.setEndValue(float(end_value))

    _track_animation(widget, key, animation)
    animation.start()
    return animation

# Animación para cambiar el ancho de un widget
def animate_width(
    widget: QWidget,
    start_width: int,
    end_width: int,
    duration: int = DURATION_STANDARD,
    key: str = "width",
) -> QParallelAnimationGroup:
    widget.setMinimumWidth(start_width)
    widget.setMaximumWidth(start_width)

    min_anim = QPropertyAnimation(widget, b"minimumWidth", widget)
    min_anim.setDuration(duration)
    min_anim.setEasingCurve(QEasingCurve.InOutCubic)
    min_anim.setStartValue(start_width)
    min_anim.setEndValue(end_width)

    max_anim = QPropertyAnimation(widget, b"maximumWidth", widget)
    max_anim.setDuration(duration)
    max_anim.setEasingCurve(QEasingCurve.InOutCubic)
    max_anim.setStartValue(start_width)
    max_anim.setEndValue(end_width)

    group = QParallelAnimationGroup(widget)
    group.addAnimation(min_anim)
    group.addAnimation(max_anim)

    def _finalize() -> None:
        widget.setFixedWidth(end_width)
        _activate_ancestors(widget)

    group.finished.connect(_finalize)

    _track_animation(widget, key, group)
    group.start()
    return group

# Animación para expandir/colapsar un widget verticalmente
def animate_collapsible(
    widget: QWidget,
    collapsed: bool,
    duration: int = DURATION_STANDARD,
    key: str = "collapsible",
) -> QPropertyAnimation:
    content_height = max(0, widget.sizeHint().height())
    current_height = max(0, widget.height())

    if collapsed:
        start_value = max(current_height, content_height)
        end_value = 0
        widget.setVisible(True)
    else:
        start_value = current_height if widget.isVisible() else 0
        end_value = content_height
        widget.setVisible(True)

    widget.setMinimumHeight(0)
    widget.setMaximumHeight(start_value)

    animation = QPropertyAnimation(widget, b"maximumHeight", widget)
    animation.setDuration(duration)
    animation.setEasingCurve(QEasingCurve.InOutCubic)
    animation.setStartValue(start_value)
    animation.setEndValue(end_value)
    animation.valueChanged.connect(lambda _: _activate_ancestors(widget))

    def _finalize() -> None:
        if collapsed:
            widget.setVisible(False)
            widget.setMaximumHeight(0)
        else:
            widget.setVisible(True)
            widget.setMaximumHeight(16777215)
        _activate_ancestors(widget)

    animation.finished.connect(_finalize)

    _track_animation(widget, key, animation)
    animation.start()
    return animation

# Animación de fade in/out
def animate_fade_transition(
    widget: QWidget,
    midpoint: Callable[[], None],
    duration: int = DURATION_STANDARD,
    key: str = "fade_transition",
) -> QSequentialAnimationGroup:
    effect = ensure_opacity_effect(widget)

    fade_out = QPropertyAnimation(effect, b"opacity", widget)
    fade_out.setDuration(max(1, duration // 2))
    fade_out.setEasingCurve(QEasingCurve.InOutCubic)
    fade_out.setStartValue(effect.opacity())
    fade_out.setEndValue(0.0)

    fade_in = QPropertyAnimation(effect, b"opacity", widget)
    fade_in.setDuration(max(1, duration // 2))
    fade_in.setEasingCurve(QEasingCurve.InOutCubic)
    fade_in.setStartValue(0.0)
    fade_in.setEndValue(1.0)

    group = QSequentialAnimationGroup(widget)
    group.addAnimation(fade_out)
    group.addAnimation(fade_in)

    def _apply_midpoint() -> None:
        midpoint()
        effect.setOpacity(0.0)

    fade_out.finished.connect(_apply_midpoint)

    _track_animation(widget, key, group)
    group.start()
    return group
