package com.particle.system.data

data class TouchEvent(
    val type: TouchEventType,
    val deviceId: String,
    val sessionId: String,
    val pointerId: Int,
    val x: Float,
    val y: Float,
    val pressure: Float,
    val holdDurationMs: Long,
    val velocityX: Float,
    val velocityY: Float,
    val trailLength: Int,
    val timestamp: Long = System.currentTimeMillis()
)

enum class TouchEventType {
    TOUCH_DOWN,
    TOUCH_MOVE,
    TOUCH_UP,
    TOUCH_BURST
}