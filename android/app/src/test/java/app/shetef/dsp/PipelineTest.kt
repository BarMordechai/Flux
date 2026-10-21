package app.shetef.dsp

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin

/** Checks the Kotlin port against expected.txt, which tests/make_android_fixtures.py wrote from the Python pipeline. */
class PipelineTest {
    private fun fixture(name: String): ByteArray =
        javaClass.getResourceAsStream("/fixtures/$name")!!.use { it.readBytes() }

    private fun readWav(name: String): FloatArray {
        val b = fixture(name)
        val dataBytes = ByteBuffer.wrap(b, 40, 4).order(ByteOrder.LITTLE_ENDIAN).int // 44-byte PCM header
        val data = ByteBuffer.wrap(b, 44, dataBytes).order(ByteOrder.LITTLE_ENDIAN).slice().order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        return FloatArray(data.remaining()) { data.get(it) / 32768f }
    }

    @Test
    fun matchesPythonReference() {
        val sr = 16000
        for (line in String(fixture("expected.txt")).lines().filter { it.isNotBlank() }) {
            val (name, mode, samples, kinds) = line.split(" ")
            val res = Pipeline.process(readWav("$name.wav"), sr, Mode.valueOf(mode.uppercase()))
            val got = res.events.joinToString(",") { it.kind.name.lowercase() }.ifEmpty { "-" }
            assertEquals("$name/$mode kinds", kinds, got)
            val diff = abs(res.audio.size - samples.toInt()) / sr.toDouble()
            assertTrue("$name/$mode length off by ${diff}s", diff < 0.02)
        }
    }

    @Test
    fun crossfadeHasNoClicks() {
        val sr = 16000
        val x = FloatArray(sr) { (0.3 * sin(2 * PI * 200 * it / sr)).toFloat() }
        val out = Edit.applyCuts(x, sr, listOf(0.3013 to 0.5507))
        assertEquals(1, out.joins.size)
        var maxStep = 0f
        for (i in 1 until out.audio.size) maxStep = maxOf(maxStep, abs(out.audio[i] - out.audio[i - 1]))
        assertTrue("max step $maxStep", maxStep < 0.05f)
    }

    @Test
    fun silenceIsUntouched() {
        val res = Pipeline.process(FloatArray(16000), 16000)
        assertTrue(res.events.isEmpty())
        assertEquals(16000, res.audio.size)
    }
}
