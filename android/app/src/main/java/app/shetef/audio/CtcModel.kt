package app.shetef.audio

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import app.shetef.dsp.Transcript
import app.shetef.dsp.Word
import org.json.JSONObject
import java.io.File
import kotlin.math.sqrt

/**
 * On-device verbatim Hebrew transcription: a wav2vec2 CTC model (int8 ONNX, bundled in assets by CI)
 * that writes what was said, repetitions included, with a time for every character.
 */
class CtcModel private constructor(ctx: Context) {
    private val env = OrtEnvironment.getEnvironment()
    private val session: OrtSession
    private val vocab: List<String>
    private val blank: Int
    private val delimiter: String
    private val normalize: Boolean

    init {
        val meta = JSONObject(ctx.assets.open("ctc.json").bufferedReader().use { it.readText() })
        val v = meta.getJSONArray("vocab")
        vocab = List(v.length()) { v.getString(it) }
        blank = meta.getInt("blank")
        delimiter = meta.optString("delimiter", "|")
        normalize = meta.optBoolean("normalize", true)
        // ORT wants a file path for a model this size; copy it out of the APK once.
        val file = File(ctx.filesDir, "ctc.onnx")
        val size = ctx.assets.openFd("ctc.onnx").use { it.length }
        if (!file.exists() || file.length() != size) {
            ctx.assets.open("ctc.onnx").use { input -> file.outputStream().use { input.copyTo(it, 1 shl 20) } }
        }
        val opts = OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(Runtime.getRuntime().availableProcessors().coerceIn(1, 4))
        }
        session = env.createSession(file.path, opts)
    }

    /** Words with character times for 16 kHz mono audio. */
    fun transcribe(x: FloatArray): List<Word> {
        val step = 30 * AudioIo.SR
        val logits = ArrayList<FloatArray>()
        var s = 0
        while (s < x.size) {
            val chunk = x.copyOfRange(s, minOf(x.size, s + step))
            if (chunk.size >= AudioIo.SR / 10) logits.addAll(run(chunk))
            s += step
        }
        return Transcript.decodeWords(logits.toTypedArray(), vocab, blank, delimiter)
    }

    private fun run(chunk: FloatArray): List<FloatArray> {
        if (normalize) {
            val mean = chunk.average()
            var v = 0.0
            for (c in chunk) v += (c - mean) * (c - mean)
            val sd = sqrt(v / chunk.size + 1e-7)
            for (i in chunk.indices) chunk[i] = ((chunk[i] - mean) / sd).toFloat()
        }
        OnnxTensor.createTensor(env, java.nio.FloatBuffer.wrap(chunk), longArrayOf(1, chunk.size.toLong())).use { input ->
            session.run(mapOf("input_values" to input)).use { out ->
                @Suppress("UNCHECKED_CAST")
                return (out[0].value as Array<Array<FloatArray>>)[0].toList()
            }
        }
    }

    companion object {
        @Volatile private var instance: CtcModel? = null

        fun isBundled(ctx: Context) = try {
            ctx.assets.openFd("ctc.onnx").close(); true
        } catch (e: Exception) {
            false
        }

        /** Loads on first use (a few seconds); null when the build has no bundled model. */
        fun get(ctx: Context): CtcModel? {
            if (!isBundled(ctx)) return null
            return instance ?: synchronized(this) { instance ?: CtcModel(ctx.applicationContext).also { instance = it } }
        }
    }
}
