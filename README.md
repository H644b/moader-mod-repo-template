# Moader mod repository template

Publish a per-game mod catalog, a browsable community storefront, gallery images, and downloadable mod ZIPs on your own host. Each package has a version, byte size, and SHA-256 checksum. Your repository owns the files and release metadata.

[Browse the working example](https://h644b.github.io/moader-mod-repo-template/) · [Example catalog](https://h644b.github.io/moader-mod-repo-template/catalog.json)

## Publish on GitHub Pages

1. Choose **Use this template → Create a new repository**. Keep the default branch named `main`.
2. Under **Settings → Pages → Build and deployment**, select **GitHub Actions**.
3. Edit `repository.json` with your workshop name and the exact 16-character Title ID and name of each game. Switch and Switch 2 editions can have different Title IDs.
4. Copy `mods/orchard-palette/` to `mods/<your-mod-id>/`. Edit `mod.json`, replace the preview images, and place your files directly under `payload/romfs/`, `payload/exefs/` or `payload/exefs_patches/`. Moader also accepts `payload/romfs.bin` and `payload/exefs.nsp`. Remove the fictional example when you are ready.
5. Push to `main` or run **Actions → Publish mod catalog → Run workflow**. Open the Pages deployment URL. Append `catalog.json` for the machine-readable feed.

For a custom domain, set the repository Actions variable `CATALOG_BASE_URL` to the full HTTPS root of your storefront, including any subpath. Configure the same domain under Pages.

## Publish on another host

With Python 3.10 or newer, run the following from the repository root.

```sh
python3 tools/build.py --base-url https://mods.example.org/workshop/
```

Upload the **contents of `_site/`** to that address. A static HTTP server is sufficient. For local inspection, serve `_site` with `python3 -m http.server --directory _site 8000`. The catalog contains absolute asset URLs under the base URL used at build time.

## Catalog contract

The public feed uses `format: "moader.catalog.v1"` and includes a host name, a description, and a `games` array. Each game has a `titleId`, a `title`, and a `mods` array. Every release has a stable ID, title, author, category, summary, description, version, publication date, license, preview URLs, and labeled HTTPS source links. The generated `download` contains `url`, `bytes`, and `sha256`. See the [sample mod](mods/orchard-palette/mod.json) for the authoring format.

- Use lowercase letters, digits, underscores, or hyphens for mod IDs, up to 48 characters. Keep the ID stable when updating a release.
- Add your own JPG or PNG files to the mod’s `previews/` directory and list the filenames in display order. Add optional community mirrors as `{"label":"Host name","url":"https://…"}` to `sources`. The builder adds your own hosted release page automatically.
- The example uses a fictional Title ID and an original palette. Use the routing Title ID from Moader for a real game and verify the package on the supported game version before publishing.
- The community Store test build downloads verified packages directly from the catalog. Additional HTTPS feeds can be added to `sdmc:/moader/store/sources.txt`, one URL per line.

The template code is MIT licensed. The Orchard sample is CC0. Green Hill Zone and its previews are by Squadaloo and carry their [original license](mods/green-hill-zone/LICENSE). Choose and state your own license for the mods you publish. The cartridge artwork and wordmark identify Moader.
