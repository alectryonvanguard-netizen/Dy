[app]
title = Sam Ng
package.name = samng
package.domain = com.samng

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,mp4,webp

# MAIN ENTRY POINT - Run Main.py (the full app)
source.main = main.py

version = 1.1.2
requirements = python3,kivy,plyer,pyjnius,requests

orientation = portrait
fullscreen = 0
# (str) Presplash of the application
presplash.filename = %(source.dir)s/logo.png

# (string) Presplash background color
android.presplash_color = black

# App Icon
icon.filename = %(source.dir)s/icon.png

android.permissions = INTERNET,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_EXTERNAL_STORAGE

android.api = 36
android.minapi = 28
android.ndk = 25b

android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
