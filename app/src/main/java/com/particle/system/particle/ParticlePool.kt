package com.particle.system.particle

class ParticlePool(val capacity: Int) {
    private val pool = ArrayDeque<Particle>(capacity)

    init { repeat(capacity) { pool.addLast(Particle()) } }

    fun acquire(): Particle? = if (pool.isEmpty()) null else pool.removeFirst()

    fun release(p: Particle) {
        p.alive = false
        pool.addLast(p)
    }

    val available: Int get() = pool.size
}