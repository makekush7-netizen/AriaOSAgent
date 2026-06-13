import React, { useRef, useEffect } from 'react'

/**
 * BackgroundCanvas — Night Garden theme
 * Lightweight particle system: 38 max gold particles drifting downward-left.
 * Pure requestAnimationFrame, <1% CPU on modern hardware.
 */
const PARTICLE_COUNT = 38
const COLORS = ['rgba(232,201,122,', 'rgba(196,165,90,', 'rgba(255,212,160,']

function createParticle(w, h) {
    const colorBase = COLORS[Math.floor(Math.random() * COLORS.length)]
    return {
        x: Math.random() * w,
        y: Math.random() * h * 0.7,
        size: 1.5 + Math.random() * 3,
        opacity: 0.05 + Math.random() * 0.3,
        dx: -0.3 + Math.random() * 0.1,
        dy: 0.15 + Math.random() * 0.4,
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.02,
        colorBase,
        phase: Math.random() * Math.PI * 2,
    }
}

export default function BackgroundCanvas() {
    const canvasRef = useRef(null)
    const particlesRef = useRef([])
    const rafRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        let w, h

        function resize() {
            w = window.innerWidth
            h = window.innerHeight
            canvas.width = w * window.devicePixelRatio
            canvas.height = h * window.devicePixelRatio
            canvas.style.width = w + 'px'
            canvas.style.height = h + 'px'
            ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0)
        }

        resize()
        window.addEventListener('resize', resize)

        // Initialize particles
        particlesRef.current = Array.from({ length: PARTICLE_COUNT }, () =>
            createParticle(w, h)
        )

        let time = 0
        function draw() {
            time += 0.016
            ctx.clearRect(0, 0, w, h)

            // Draw ambient glow behind character area (left-center)
            const grd = ctx.createRadialGradient(w * 0.28, h * 0.55, 0, w * 0.28, h * 0.55, 200)
            grd.addColorStop(0, 'rgba(232,201,122,0.04)')
            grd.addColorStop(1, 'transparent')
            ctx.fillStyle = grd
            ctx.fillRect(0, 0, w, h)

            // Draw stars (static, upper quarter)
            if (!draw._stars) {
                draw._stars = Array.from({ length: 8 }, () => ({
                    x: Math.random() * w,
                    y: Math.random() * h * 0.25,
                    r: 0.5 + Math.random() * 1,
                    o: 0.2 + Math.random() * 0.3,
                }))
            }
            for (const star of draw._stars) {
                ctx.beginPath()
                ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2)
                ctx.fillStyle = `rgba(240,237,232,${star.o * (0.7 + 0.3 * Math.sin(time * 0.5 + star.x))})`
                ctx.fill()
            }

            // Draw particles
            for (const p of particlesRef.current) {
                p.x += p.dx
                p.y += p.dy
                p.rotation += p.rotSpeed

                // Gentle sine drift
                p.x += Math.sin(time * 0.8 + p.phase) * 0.08

                // Respawn when off screen
                if (p.y > h + 10 || p.x < -10) {
                    p.x = Math.random() * w
                    p.y = -5
                    p.opacity = 0.05 + Math.random() * 0.3
                }

                // Fade in/out near edges
                let alpha = p.opacity
                if (p.y < 20) alpha *= p.y / 20
                if (p.y > h - 40) alpha *= (h - p.y) / 40

                ctx.save()
                ctx.translate(p.x, p.y)
                ctx.rotate(p.rotation)
                ctx.fillStyle = p.colorBase + alpha + ')'
                // Draw as small ellipse (blossom petal shape)
                ctx.beginPath()
                ctx.ellipse(0, 0, p.size, p.size * 0.6, 0, 0, Math.PI * 2)
                ctx.fill()
                ctx.restore()
            }

            rafRef.current = requestAnimationFrame(draw)
        }

        draw()

        return () => {
            window.removeEventListener('resize', resize)
            if (rafRef.current) cancelAnimationFrame(rafRef.current)
        }
    }, [])

    return (
        <canvas
            ref={canvasRef}
            style={{
                position: 'fixed',
                inset: 0,
                zIndex: 0,
                pointerEvents: 'none',
            }}
        />
    )
}