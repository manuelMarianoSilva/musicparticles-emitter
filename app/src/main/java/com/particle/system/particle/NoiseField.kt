package com.particle.system.particle

import kotlin.math.floor

class NoiseField {

    private val perm = IntArray(512).also { p ->
        val base = (0..255).toMutableList()
        base.shuffle()
        for (i in 0..255) { p[i] = base[i]; p[i + 256] = base[i] }
    }

    fun sample(x: Float, y: Float, life: Float): Pair<Float, Float> {
        val scale = 0.003f
        val t = (1f - life) * 2f
        val nx = noise(x * scale + t, y * scale)
        val ny = noise(x * scale, y * scale + t + 100f)
        return Pair(nx * 2f - 1f, ny * 2f - 1f)
    }

    private fun fade(t: Double) = t * t * t * (t * (t * 6 - 15) + 10)
    private fun lerp(t: Double, a: Double, b: Double) = a + t * (b - a)
    private fun grad(hash: Int, x: Double, y: Double): Double {
        val h = hash and 3
        val u = if (h < 2) x else y
        val v = if (h < 2) y else x
        return (if (h and 1 == 0) u else -u) + (if (h and 2 == 0) v else -v)
    }

    private fun noise(xf: Float, yf: Float): Float {
        val xi = floor(xf.toDouble()).toInt() and 255
        val yi = floor(yf.toDouble()).toInt() and 255
        val x = xf - floor(xf.toDouble())
        val y = yf - floor(yf.toDouble())
        val u = fade(x.toDouble())
        val v = fade(y.toDouble())
        val a  = perm[xi    ] + yi
        val b  = perm[xi + 1] + yi
        val aa = perm[a     ]
        val ab = perm[a  + 1]
        val ba = perm[b     ]
        val bb = perm[b  + 1]
        return lerp(v,
            lerp(u, grad(perm[aa], x, y),     grad(perm[ba], x - 1, y)),
            lerp(u, grad(perm[ab], x, y - 1), grad(perm[bb], x - 1, y - 1))
        ).toFloat() * 0.5f + 0.5f
    }
}