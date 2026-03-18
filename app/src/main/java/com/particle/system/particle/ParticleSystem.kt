package com.particle.system.particle

class ParticleSystem(capacity: Int = 20_000) {

    private val pool      = ParticlePool(capacity)
    private val noise     = NoiseField()
    val liveParticles     = mutableListOf<Particle>()
    private val toRelease = mutableListOf<Particle>()

    @Synchronized
    fun spawn(x: Float, y: Float, vx: Float, vy: Float,
              size: Float, hue: Float, lifeSec: Float) {
        val p = pool.acquire() ?: recycleOldest() ?: return
        p.init(x, y, vx, vy, size, hue, lifeSec)
        liveParticles.add(p)
    }

    @Synchronized
    fun update(dtMs: Float) {
        toRelease.clear()
        for (p in liveParticles) {
            p.update(dtMs, noise)
            if (!p.alive) toRelease.add(p)
        }
        for (p in toRelease) {
            liveParticles.remove(p)
            pool.release(p)
        }
    }

    private fun recycleOldest(): Particle? {
        if (liveParticles.isEmpty()) return null
        return liveParticles.removeAt(0)
    }

    val liveCount: Int get() = liveParticles.size
}