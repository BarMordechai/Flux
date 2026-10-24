plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val buildNumber = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()

android {
    namespace = "app.shetef"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.shetef"
        minSdk = 26
        targetSdk = 35
        versionCode = buildNumber
        versionName = "0.1.$buildNumber"
        // The processing server (a Hugging Face Space); CI fills it in. Empty = offline only.
        buildConfigField("String", "SERVER_URL", "\"${System.getenv("SHETEF_SERVER_URL") ?: ""}\"")
        buildConfigField("String", "API_KEY", "\"${System.getenv("SHETEF_API_KEY") ?: "shetef-mvp-3f9c1a"}\"")
    }

    buildFeatures {
        buildConfig = true
    }

    signingConfigs {
        // A fixed key checked into the repo so every CI build can update the previous install.
        // Fine for testing; a Play Store release needs a private key kept in CI secrets instead.
        create("shared") {
            storeFile = file("shetef-test.keystore")
            storePassword = "shetef-test"
            keyAlias = "shetef"
            keyPassword = "shetef-test"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("shared")
        }
        debug {
            signingConfig = signingConfigs.getByName("shared")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core:1.13.1")
    testImplementation("junit:junit:4.13.2")
}
