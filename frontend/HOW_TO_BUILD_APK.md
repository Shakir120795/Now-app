# Build the NOW app APK on GitHub (no installs on your PC)

1. Go to https://github.com/new and create a repository (name: `now-app`, keep it Private).
2. On the new repo page click **"uploading an existing file"**.
3. Drag **everything** from this extracted folder into the upload box — including the
   hidden **`.github`** folder — then click **Commit changes**.
4. Open the **Actions** tab. A workflow **"Build APK"** runs automatically (~5–8 min).
5. When it finishes (green ✓), open the run and download the **`now-app-apk`** artifact.
   Unzip it → `app-release.apk`.
6. Copy the APK to your Android phone, tap it, allow "install from unknown sources", install.

> The app opens to onboarding/login with the real design. To load live products/orders,
> your backend must be reachable from the phone — change `API_BASE_URL` in
> `.github/workflows/build-apk.yml` to your backend address and re-run the build.

If the `.github` folder didn't upload (some PCs hide it): in the repo click
**Add file → Create new file**, type the name
`.github/workflows/build-apk.yml`, paste the contents of that file, and commit.
