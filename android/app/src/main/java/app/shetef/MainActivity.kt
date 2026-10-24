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
import app.shetef.audio.CloudClient
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
    @Volatile private var cloud: CloudClient.Response? = null // worker thread only
    @Volatile private var cloudFor: FloatArray? = null
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
            mode = when (id) {
                R.id.modeFull -> Mode.FULL
                R.id.modeStrong -> Mode.STRONG
                else -> Mode.GENTLE
            }
            modeHint.setText(
                when (mode) {
                    Mode.FULL -> R.string.mode_full_hint
                    Mode.STRONG -> R.string.mode_strong_hint
                    else -> R.string.mode_gentle_hint
                },
            )
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
        findViewById<Button>(R.id.shareOriginal).setOnClickListener { share(whatsApp = false, original = true) }
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

    /** What one smoothing produced, from the server or from on-device silence shortening. */
    private class Outcome(
        val file: File,
        val counts: Map<Kind, Int>,
        val events: List<Triple<Kind, Double, Double>>,
        val outSeconds: Double,
        val transcript: String?,
        val note: Int? = null,
    )

    private fun smooth(x: FloatArray) {
        stopPlayback()
        input = x
        status.setText(R.string.processing)
        result.visibility = View.GONE
        val m = mode
        worker.execute {
            try {
                val dir = File(cacheDir, "shared").apply { mkdirs() }
                if (cloudFor !== x) { // new message: send it once, every mode comes back
                    dir.listFiles()?.forEach { it.delete() }
                    val orig = File(dir, "original.wav").also { AudioIo.writeWav(x, AudioIo.SR, it) }
                    originalFile = orig
                    cloud = if (CloudClient.enabled) {
                        ui.post { status.setText(R.string.sending) }
                        try {
                            CloudClient.processAll(orig) { ui.post { status.setText(R.string.server_waking) } }
                        } catch (e: Exception) {
                            null
                        }
                    } else null
                    cloudFor = x
                }
                val outcome = cloud?.results?.get(m.name.lowercase())?.let { fromCloud(it, dir, cloud?.transcript, m) }
                    ?: local(x, m, dir)
                ui.post { show(outcome, x.size) }
            } catch (e: Exception) {
                ui.post { status.text = getString(R.string.process_failed, e.message ?: "") }
            }
        }
    }

    private fun kindOf(s: String) = when (s) {
        "repetition" -> Kind.REPETITION
        "prolongation" -> Kind.PROLONGATION
        "block" -> Kind.BLOCK
        "pause" -> Kind.PAUSE
        else -> Kind.EDGE
    }

    private fun fromCloud(r: CloudClient.ModeResult, dir: File, transcript: String?, m: Mode): Outcome {
        val file = File(dir, "voice-message-${m.name.lowercase()}-${System.currentTimeMillis() / 1000}.m4a")
        file.writeBytes(r.audio)
        val counts = HashMap<Kind, Int>()
        val c = r.report.getJSONObject("counts")
        for (k in c.keys()) counts[kindOf(k)] = c.getInt(k)
        val ev = r.report.getJSONArray("events")
        val events = List(ev.length()) {
            val e = ev.getJSONObject(it)
            Triple(kindOf(e.getString("kind")), e.getDouble("start"), e.getDouble("end"))
        }
        return Outcome(file, counts, events, r.report.getDouble("output_seconds"), transcript)
    }

    /** Offline fallback: only silences are shortened, words are never touched. */
    private fun local(x: FloatArray, m: Mode, dir: File): Outcome {
        val res = Pipeline.process(x, AudioIo.SR, m)
        val file = File(dir, "voice-message-local-${System.currentTimeMillis() / 1000}.m4a")
        AudioIo.encodeM4a(res.audio, res.sr, file)
        return Outcome(
            file,
            Kind.values().associateWith { res.count(it) },
            res.events.map { Triple(it.kind, it.start, it.end) },
            res.audio.size.toDouble() / res.sr,
            null,
            R.string.offline_note,
        )
    }

    private fun show(o: Outcome, inSamples: Int) {
        outputFile = o.file
        val parts = listOf(
            Kind.REPETITION to R.string.k_repetition,
            Kind.PROLONGATION to R.string.k_prolongation,
            Kind.BLOCK to R.string.k_block,
            Kind.PAUSE to R.string.k_pause,
        ).mapNotNull { (k, label) -> (o.counts[k] ?: 0).takeIf { it > 0 }?.let { "${getString(label)}: $it" } }
        val before = inSamples.toDouble() / AudioIo.SR
        summary.text = if (parts.isEmpty()) getString(R.string.nothing_found)
        else getString(R.string.summary, parts.joinToString(" · "), fmt(before), fmt(o.outSeconds))
        val lines = o.events.filter { it.first != Kind.EDGE }.map {
            getString(R.string.event_line, getString(label(it.first)), fmt(it.second), fmt(it.third))
        }
        val heard = o.transcript?.let { getString(R.string.heard, it) }
        details.text = (lines + listOfNotNull(heard)).joinToString("\n")
        status.text = o.note?.let { getString(it) } ?: ""
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

    private fun share(whatsApp: Boolean, original: Boolean = false) {
        val file = (if (original) originalFile else outputFile) ?: return
        stopPlayback()
        val uri = FileProvider.getUriForFile(this, "$packageName.files", file)
        val send = Intent(Intent.ACTION_SEND).apply {
            type = if (original) "audio/wav" else "audio/mp4"
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
