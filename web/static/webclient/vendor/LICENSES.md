# Vendored WebClient runtime assets

The WebClient shell must make no remote request for a runtime UI dependency.
The following pinned assets are served from the project origin under
`web/static/webclient/vendor/`. SHA-256 digests are provided for
reproducibility; if a pinned file changes, update this record and the
repository contract test.

## jQuery 3.2.1

- File: `js/jquery-3.2.1.min.js`
- Source: `https://code.jquery.com/jquery-3.2.1.min.js`
- Version: 3.2.1
- License: MIT (Copyright JS Foundation and other contributors, `jquery.org/license`)
- SHA-256: `87083882cc6015984eb0411a99d3981817f5dc5c90ba24f0940420c5548d82de`

## GoldenLayout 1.x

- Files: `js/goldenlayout.min.js`, `css/goldenlayout-base.css`,
  `css/goldenlayout-dark-theme.css`
- Source:
  - `https://golden-layout.com/files/latest/js/goldenlayout.min.js`
  - `https://golden-layout.com/files/latest/css/goldenlayout-base.css`
  - `https://golden-layout.com/files/latest/css/goldenlayout-dark-theme.css`
- Version: GoldenLayout 1.x (latest snapshot served by golden-layout.com on
  2026-08-02; the minified bundle does not embed a version string)
- License: MIT
- SHA-256:
  - `js/goldenlayout.min.js`: `0981b4e8a4a7d06915b282285e0ceb3bdf1bae188a6791a1cfde6fb7970d3104`
  - `css/goldenlayout-base.css`: `57e9905abfcbf483cf17dcb9a78d96d8f961bc43405c416828481a5eb54bbcca`
  - `css/goldenlayout-dark-theme.css`: `ca0c3c3ef4832495062dfe90f4a210b1847798e9a240d9436b130b0cec7dc4bd`

## License texts

Both jQuery and GoldenLayout are distributed under the MIT License:

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
