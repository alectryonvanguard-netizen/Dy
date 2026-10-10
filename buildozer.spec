[app]

title = Sam Ng
package.name = samng
package.domain = com.samng

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,mp4,webp

version = 1.0.0

requirements = python3,kivy,plyer,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 23
android.ndk = 25b

android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.bootstrap = sdl2

[buildozer]

log_level = 2
warn_on_root = 1
