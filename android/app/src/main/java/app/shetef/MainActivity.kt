package app.shetef

import android.Manifest
import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Intent
import android.content.pm.PackageManager
import android.media.MediaPlayer
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Button
import android.widget.RadioGroup
import android.widget.TextView
import androidx.core.content.FileProvider
import app.shetef.audio.AudioIo
import app.shetef.audio.Recorder
import app.shetef.dsp.Kind
import app.shetef.dsp.Mode
import app.shetef.dsp.Pipeline
import java.io.File
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private val ui = Handler(Looper.getMainLooper())
    private var recorder: Recorder? = null
    private var mode = Mode.GENTLE
    private var input: FloatArray? = null
    private var originalFile: File? = null
    private var outputFile: File? = null
    private var player: MediaPlayer? = null
    private var playing: Button? = null

    private lateinit var recBtn: Button
    private lateinit var timer: TextView
    private lateinit var status: TextView
    private lateinit var result: View
    private lateinit var summary: TextView
    private lateinit var details: TextView
    private lateinit var modeHint: TextView
    private lateinit var playAfter: Button
    private lateinit var playBefore: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        recBtn = findViewById(R.id.recBtn)
        timer = findViewById(R.id.timer)
        status = findViewById(R.id.status)
        result = findViewById(R.id.result)
        summary = findViewById(R.id.summary)
        details = findViewById(R.id.details)
        modeHint = findViewById(R.id.modeHint)
        playAfter = findViewById(R.id.playAfter)
        playBefore = findViewById(R.id.playBefore)

        findViewById<RadioGroup>(R.id.modeGroup).setOnCheckedChangeListener { _, id ->
            mode = if (id == R.id.modeFull) Mode.FULL else Mode.GENTLE
            modeHint.setText(if (mode == Mode.FULL) R.string.mode_full_hint else R.string.mode_gentle_hint)
            input?.let { smooth(it) } // re-smooth the same message with the new setting
        }
        recBtn.setOnClickListener { toggleRecording() }
        findViewById<Button>(R.id.pickBtn).setOnClickListener {
            stopPlayback()
            startActivityForResult(Intent(Intent.ACTION_GET_CONTENT).setType("audio/*"), REQ_PICK)
        }
        playAfter.setOnClickListener { togglePlay(playAfter, outputFile) }
        playBefore.setOnClickListener { togglePlay(playBefore, originalFile) }
        findViewById<Button>(R.id.shareWhatsApp).setOnClickListener { share(whatsApp = true) }
        findViewById<Button>(R.id.shareOther).setOnClickListener { share(whatsApp = false) }
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    /** A voice note shared into the app from WhatsApp or any other app. */
    private fun handleIntent(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val uri = if (Build.VERSION.SDK_INT >= 33) {
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        } else {
            @Suppress("DEPRECATION") intent.getParcelableExtra(Intent.EXTRA_STREAM)
        }
        uri?.let { load(it) }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_PICK && resultCode == RESULT_OK) data?.data?.let { load(it) }
    }

    // ------------------------------------------------------------------ recording

    private fun toggleRecording() {
        val rec = recorder
        if (rec != null) {
            finishRecording(rec)
            return
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC)
            return
        }
        stopPlayback()
        result.visibility = View.GONE
        status.text = ""
        recorder = Recorder().also { it.start() }
        recBtn.setText(R.string.stop)
        recBtn.setBackgroundResource(R.drawable.rec_on)
        tick()
    }

    private fun tick() {
        val rec = recorder ?: return
        val s = rec.seconds.toInt()
        timer.text = String.format(Locale.US, "%d:%02d", s / 60, s % 60)
        if (!rec.isRecording) finishRecording(rec) else ui.postDelayed({ tick() }, 250)
    }

    private fun finishRecording(rec: Recorder) {
        recorder = null
        recBtn.setText(R.string.record)
        recBtn.setBackgroundResource(R.drawable.rec_idle)
        val x = rec.stop()
        if (x.size < AudioIo.SR / 2) {
            status.setText(R.string.too_short)
            return
        }
        smooth(x)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        if (requestCode == REQ_MIC) {
            if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) toggleRecording()
            else status.setText(R.string.no_mic)
        }
    }

    // ------------------------------------------------------------------ processing

    private fun load(uri: Uri) {
        status.setText(R.string.reading)
        result.visibility = View.GONE
        worker.execute {
            try {
                val x = AudioIo.decode(this, uri)
                ui.post { smooth(x) }
            } catch (e: Exception) {
                ui.post { status.text = getString(R.string.read_failed) }
            }
        }
    }

    private fun smooth(x: FloatArray) {
        stopPlayback()
        input = x
        status.setText(R.string.processing)
        result.visibility = View.GONE
        val m = mode
        worker.execute {
            try {
                val dir = File(cacheDir, "shared").apply { mkdirs(); listFiles()?.forEach { it.delete() } }
                val orig = File(dir, "original.wav").also { AudioIo.writeWav(x, AudioIo.SR, it) }
                val res = Pipeline.process(x, AudioIo.SR, m)
                val out = File(dir, "voice-message-${System.currentTimeMillis() / 1000}.m4a")
                AudioIo.encodeM4a(res.audio, res.sr, out)
                ui.post { show(res, x.size, orig, out) }
            } catch (e: Exception) {
                ui.post { status.text = getString(R.string.process_failed, e.message ?: "") }
            }
        }
    }

    private fun show(res: Pipeline.Result, inSamples: Int, orig: File, out: File) {
        originalFile = orig
        outputFile = out
        val parts = listOf(
            Kind.REPETITION to R.string.k_repetition,
            Kind.PROLONGATION to R.string.k_prolongation,
            Kind.BLOCK to R.string.k_block,
            Kind.PAUSE to R.string.k_pause,
        ).mapNotNull { (k, label) -> res.count(k).takeIf { it > 0 }?.let { "${getString(label)}: $it" } }
        val before = inSamples.toDouble() / AudioIo.SR
        val after = res.audio.size.toDouble() / res.sr
        summary.text = if (parts.isEmpty()) getString(R.string.nothing_found)
        else getString(R.string.summary, parts.joinToString(" · "), fmt(before), fmt(after))
        details.text = res.events.filter { it.kind != Kind.EDGE }.joinToString("\n") {
            getString(R.string.event_line, getString(label(it.kind)), fmt(it.start), fmt(it.end))
        }
        status.text = ""
        result.visibility = View.VISIBLE
    }

    private fun label(k: Kind) = when (k) {
        Kind.REPETITION -> R.string.k_repetition
        Kind.PROLONGATION -> R.string.k_prolongation
        Kind.BLOCK -> R.string.k_block
        else -> R.string.k_pause
    }

    private fun fmt(s: Double) = String.format(Locale.US, "%.1f", s)

    // ------------------------------------------------------------------ playback & sharing

    private fun togglePlay(btn: Button, file: File?) {
        val wasThis = playing == btn
        stopPlayback()
        if (wasThis || file == null) return
        player = MediaPlayer().apply {
            setDataSource(file.path)
            setOnCompletionListener { stopPlayback() }
            prepare()
            start()
        }
        playing = btn
        btn.setText(R.string.stop_playing)
    }

    private fun stopPlayback() {
        player?.release()
        player = null
        playAfter.setText(R.string.play_after)
        playBefore.setText(R.string.play_before)
        playing = null
    }

    private fun share(whatsApp: Boolean) {
        val file = outputFile ?: return
        stopPlayback()
        val uri = FileProvider.getUriForFile(this, "$packageName.files", file)
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "audio/mp4"
            putExtra(Intent.EXTRA_STREAM, uri)
            clipData = ClipData.newRawUri("", uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        if (whatsApp) {
            for (pkg in listOf("com.whatsapp", "com.whatsapp.w4b")) {
                try {
                    startActivity(Intent(send).setPackage(pkg))
                    return
                } catch (_: ActivityNotFoundException) {
                }
            }
        }
        startActivity(Intent.createChooser(send, getString(R.string.share_title)))
    }

    override fun onDestroy() {
        recorder?.stop()
        player?.release()
        worker.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val REQ_PICK = 1
        private const val REQ_MIC = 2
    }
}
