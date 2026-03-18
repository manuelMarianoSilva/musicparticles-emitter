package com.particle.system.particle

import kotlin.math.*

class Particle {
    var x = 0f; var y = 0f
    var vx = 0f; var vy = 0f
    var life = 1f
    var maxLife = 1f
    var size = 8f
    var r = 1f; var g = 1f; var b = 1f
    var hue = 0f
    var alive = false

    companion object {
        const val GRAVITY = 0f // 0.00035f
        const val DRAG    = 0.983f
    }

    fun update(dtMs: Float, noise: NoiseField) {
        if (!alive) return
        val (nx, ny) = noise.sample(x, y, life)
        vx += nx * 0.05f; vy += ny * 0.05f
        vy += GRAVITY * dtMs
        vx *= DRAG; vy *= DRAG
        x += vx * dtMs; y += vy * dtMs
        val speed = sqrt(vx * vx + vy * vy)
        hue = (hue + speed * 0.6f) % 360f
        hslToRgb(hue, 0.9f, 0.62f).also { (rr, gg, bb) -> r = rr; g = gg; b = bb }
        life -= dtMs / (maxLife * 1000f)
        if (life <= 0f) alive = false
    }

    fun init(px: Float, py: Float, pvx: Float, pvy: Float,
             pSize: Float, pHue: Float, lifeSec: Float) {
        x = px; y = py; vx = pvx; vy = pvy
        size = pSize; hue = pHue; maxLife = lifeSec; life = 1f; alive = true
        hslToRgb(hue, 0.9f, 0.62f).also { (rr, gg, bb) -> r = rr; g = gg; b = bb }
    }
}

fun hslToRgb(h: Float, s: Float, l: Float): Triple<Float, Float, Float> {
    val c = (1f - abs(2f * l - 1f)) * s
    val xv = c * (1f - abs((h / 60f) % 2f - 1f))
    val m = l - c / 2f
    val (r, g, b) = when ((h / 60f).toInt() % 6) {
        0 -> Triple(c, xv, 0f); 1 -> Triple(xv, c, 0f); 2 -> Triple(0f, c, xv)
        3 -> Triple(0f, xv, c); 4 -> Triple(xv, 0f, c); else -> Triple(c, 0f, xv)
    }
    return Triple(r + m, g + m, b + m)
}