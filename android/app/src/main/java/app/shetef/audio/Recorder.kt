package app.shetef.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import app.shetef.dsp.FloatBuffer
import kotlin.concurrent.thread

/** Records mono 16 kHz PCM straight into memory. Nothing touches the disk until processing is done. */
class Recorder {
    private var record: AudioRecord? = null
    private var worker: Thread? = null
    @Volatile private var running = false
    private val buffer = FloatBuffer()

    val seconds: Double get() = buffer.size.toDouble() / AudioIo.SR

    @SuppressLint("MissingPermission") // the activity asks for RECORD_AUDIO before calling start()
    fun start() {
        val min = AudioRecord.getMinBufferSize(AudioIo.SR, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val rec = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION, // no aggressive AGC/noise gating that would hide blocks
            AudioIo.SR, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(min, AudioIo.SR),
        )
        record = rec
        running = true
        rec.startRecording()
        worker = thread(name = "recorder") {
            val chunk = ShortArray(1600)
            while (running) {
                val n = rec.read(chunk, 0, chunk.size)
                if (n > 0) synchronized(buffer) { for (i in 0 until n) buffer.add(chunk[i] / 32768f) }
                if (seconds > MAX_SECONDS) running = false
            }
        }
    }

    val isRecording: Boolean get() = running

    fun stop(): FloatArray {
        running = false
        worker?.join()
        record?.run { stop(); release() }
        record = null
        return synchronized(buffer) { buffer.toArray() }
    }

    companion object {
        const val MAX_SECONDS = 600.0
    }
}
