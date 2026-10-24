package app.shetef.audio

import android.util.Base64
import app.shetef.BuildConfig
import org.json.JSONObject
import java.io.DataOutputStream
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * Word-guided smoothing on the Shetef server (ivrit.ai Hebrew recogniser). The recording is sent once and
 * comes back processed in every mode, so switching modes needs no second upload. The server keeps nothing.
 */
object CloudClient {
    val enabled: Boolean get() = BuildConfig.SERVER_URL.isNotEmpty()

    class ModeResult(val audio: ByteArray, val report: JSONObject)
    class Response(val transcript: String?, val results: Map<String, ModeResult>)

    /** [onWaiting] is called while a sleeping server starts up (free hosting sleeps when idle). */
    fun processAll(wav: File, onWaiting: () -> Unit): Response {
        var lastError: IOException? = null
        repeat(12) { attempt ->
            try {
                return post(wav)
            } catch (e: ServerStarting) {
                lastError = e
                onWaiting()
                Thread.sleep(if (attempt < 3) 5_000 else 15_000)
            }
        }
        throw lastError ?: IOException("server unavailable")
    }

    private class ServerStarting(code: Int) : IOException("server starting ($code)")

    private fun post(wav: File): Response {
        val boundary = "----shetef${System.nanoTime()}"
        val conn = URL(BuildConfig.SERVER_URL.trimEnd('/') + "/api/process_all").openConnection() as HttpURLConnection
        try {
            conn.connectTimeout = 30_000
            conn.readTimeout = 300_000
            conn.doOutput = true
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            conn.setRequestProperty("X-Api-Key", BuildConfig.API_KEY)
            conn.setChunkedStreamingMode(64 * 1024)
            DataOutputStream(conn.outputStream).use { o ->
                fun field(name: String, value: String) {
                    o.writeBytes("--$boundary\r\nContent-Disposition: form-data; name=\"$name\"\r\n\r\n$value\r\n")
                }
                field("fmt", "m4a")
                field("language", "he")
                o.writeBytes("--$boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"message.wav\"\r\n")
                o.writeBytes("Content-Type: audio/wav\r\n\r\n")
                wav.inputStream().use { it.copyTo(o) }
                o.writeBytes("\r\n--$boundary--\r\n")
            }
            val code = conn.responseCode
            if (code == 502 || code == 503 || code == 504) throw ServerStarting(code)
            if (code != 200) throw IOException("server error $code")
            val j = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
            val res = j.getJSONObject("results")
            val out = HashMap<String, ModeResult>()
            for (mode in res.keys()) {
                val r = res.getJSONObject(mode)
                out[mode] = ModeResult(Base64.decode(r.getString("audio"), Base64.DEFAULT), r.getJSONObject("report"))
            }
            return Response(if (j.isNull("transcript")) null else j.getString("transcript"), out)
        } finally {
            conn.disconnect()
        }
    }
}
