package com.particle.system.particle

import kotlin.math.*
import kotlin.random.Random

class ParticleEmitter(private val system: ParticleSystem) {

    private val rng = Random.Default

    fun onTouchDown(x: Float, y: Float, pressure: Float, baseHue: Float? = null) {
        val count = (20 + pressure * 30).toInt()
        val hue = baseHue ?: rng.nextFloat() * 360f
        repeat(count) {
            val angle = rng.nextFloat() * 2f * PI.toFloat()
            val speed = rng.nextFloat() * 0.4f + 0.1f
            system.spawn(x, y, cos(angle) * speed, sin(angle) * speed,
                rng.nextFloat() * 10f + 4f,
                (hue + rng.nextFloat() * 40f) % 360f,
                rng.nextFloat() * 3f + 2f)
        }
    }

    fun onTouchMove(x: Float, y: Float, vx: Float, vy: Float, baseHue: Float? = null) {
        val speed = sqrt(vx * vx + vy * vy)
        val count = (speed * 8f).toInt().coerceIn(3, 30)
        val hue = baseHue ?: (atan2(vy, vx) * (180f / PI.toFloat()) + 360f) % 360f
        val spread = 0.15f
        repeat(count) {
            system.spawn(
                x + rng.nextFloat() * 6f - 3f,
                y + rng.nextFloat() * 6f - 3f,
                vx * 0.3f + (rng.nextFloat() - 0.5f) * spread,
                vy * 0.3f + (rng.nextFloat() - 0.5f) * spread,
                rng.nextFloat() * 7f + 2f,
                (hue + rng.nextFloat() * 60f) % 360f,
                rng.nextFloat() * 2f + 1f)
        }
    }

    fun onBurst(x: Float, y: Float, holdMs: Long, baseHue: Float? = null) {
        val holdFactor = (holdMs / 5000f).coerceIn(0f, 1f)
        val count = (50 + holdFactor * 158).toInt()
        val hue = baseHue ?: (rng.nextFloat() * 360f)
        val maxSpeed = 0.3f + holdFactor * 1.2f
        repeat(count) {
            val angle = rng.nextFloat() * 2f * PI.toFloat()
            system.spawn(x, y,
                cos(angle) * rng.nextFloat() * maxSpeed,
                sin(angle) * rng.nextFloat() * maxSpeed,
                rng.nextFloat() * (8f + holdFactor * 16f) + 3f,
                (hue + rng.nextFloat() * 80f) % 360f,
                rng.nextFloat() * 4f + 2f)
        }
    }

    fun onTouchUp(x: Float, y: Float, holdMs: Long) {
        val count = (20 + (holdMs / 100f).toInt()).coerceAtMost(80)
        val baseHue = rng.nextFloat() * 360f
        repeat(count) {
            val angle = rng.nextFloat() * 2f * PI.toFloat()
            system.spawn(x, y,
                cos(angle) * (rng.nextFloat() * 0.5f + 0.05f),
                sin(angle) * (rng.nextFloat() * 0.5f + 0.05f) - 0.3f,
                rng.nextFloat() * 8f + 2f,
                (baseHue + rng.nextFloat() * 60f) % 360f,
                rng.nextFloat() * 3f + 1.5f)
        }
    }
}