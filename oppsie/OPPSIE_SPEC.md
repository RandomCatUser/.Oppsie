# The `.oppsie` Image Format Specification
**Version 1.0**

The `.oppsie` image format is a lightweight, fast, and simple image format designed for high-speed lossless (and optionally lossy) image compression. It is heavily inspired by QOI (Quite OK Image Format) and is optimized for simple implementation, high-speed encoding/decoding, and reasonable compression ratios.

---

## File Structure

An `.oppsie` file consists of a 15-byte header, followed by a sequence of variable-length pixel chunks, and ends with an 8-byte end marker.

```
┌─────────────────┐
│     Header      │  15 bytes
├─────────────────┤
│  Pixel Chunks   │  Variable length
├─────────────────┤
│   End Marker    │  8 bytes
└─────────────────┘
```

---

## The Header

The header is 15 bytes long and has the following layout (all multibyte integers are big-endian):

```
┌───────────────┬─────────────────┬──────────────────┬──────────────┬──────────────┬──────────────┐
│  Magic Bytes  │  Width (w)      │  Height (h)      │  Channels    │  Colorspace  │    Flags     │
│    "OPPS"     │  32-bit uint    │  32-bit uint     │  8-bit uint  │  8-bit uint  │  8-bit uint  │
│  [0 - 3]      │  [4 - 7]        │  [8 - 11]        │  [12]        │  [13]        │  [14]        │
└───────────────┴─────────────────┴──────────────────┴──────────────┴──────────────┴──────────────┘
```

*   **Magic Bytes (4 bytes)**: The ASCII characters `"OPPS"` (`0x4F 0x50 0x50 0x53`).
*   **Width (4 bytes)**: Image width in pixels (big-endian).
*   **Height (4 bytes)**: Image height in pixels (big-endian).
*   **Channels (1 byte)**:
    *   `3` = RGB (no alpha)
    *   `4` = RGBA (with alpha)
*   **Colorspace (1 byte)**:
    *   `0` = sRGB with linear alpha
    *   `1` = All channels linear
*   **Flags (1 byte)**:
    *   `0x00`: Lossless mode (default).
    *   `0x01` to `0x07`: Lossy quantization level. If non-zero, indicates that the `N` least significant bits of the red, green, and blue color channels are quantized (cleared via bitwise operations) during encoding to improve compression performance.

---

## The Pixel Stream

The pixel stream contains a sequence of pixel values. The image is encoded in row-major order (left-to-right, top-to-bottom).

During encoding and decoding, the codec maintains:
1.  A **running palette** array of 64 pixels initialized to `(0, 0, 0, 0)` (RGBA).
2.  A **previous pixel** value initialized to `(0, 0, 0, 255)`.
3.  A **run length** tracker for repeating pixels.

### Running Palette Indexing
For each pixel, its position in the running palette of 64 entries is calculated using the following hash function:
$$\text{index} = (R \times 3 + G \times 5 + B \times 7 + A \times 11) \pmod{64}$$

Whenever a pixel is processed (either read or written), it is inserted into the running palette at this calculated index.

---

## Chunk Types

A pixel chunk is a variable-length byte sequence starting with a tag that determines how the pixel is decoded.

### 1. `OPPS_INDEX` Chunk (1 byte)
Used when the current pixel matches the pixel stored in the running palette at the calculated index.

```
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 0 │ 0 │         Index         │
└───┴───┴───┴───┴───┴───┴───┴───┘
```
*   **Tag**: `00` (2 bits)
*   **Index**: 6-bit index (`0` to `63`) in the running palette.
*   **Byte Range**: `0x00` - `0x3F`

### 2. `OPPS_DIFF` Chunk (1 byte)
Used when the alpha value of the current pixel is identical to the previous pixel, and the red, green, and blue differences from the previous pixel are small (between `-2` and `+1`).

```
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 0 │ 1 │   dr  │   dg  │   db  │
└───┴───┴───┴───┴───┴───┴───┴───┘
```
*   **Tag**: `01` (2 bits)
*   **dr**: Red difference biased by 2 (2 bits: `00` = -2, `01` = -1, `10` = 0, `11` = +1).
*   **dg**: Green difference biased by 2 (2 bits: `00` = -2, `01` = -1, `10` = 0, `11` = +1).
*   **db**: Blue difference biased by 2 (2 bits: `00` = -2, `01` = -1, `10` = 0, `11` = +1).
*   **Byte Range**: `0x40` - `0x7F`

### 3. `OPPS_LUMA` Chunk (2 bytes)
Used when the alpha value of the current pixel is identical to the previous pixel, and the green difference is moderate (between `-32` and `+31`), while the red and blue differences relative to the green difference are small (between `-8` and `+7`).

```
Byte 1:
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 1 │ 0 │        diff green     │
└───┴───┴───┴───┴───┴───┴───┴───┘
Byte 2:
┌───┬───┬───┬───┬───┬───┬───┬───┐
│     dr - dg   │    db - dg    │
└───┴───┴───┴───┴───┴───┴───┴───┘
```
*   **Tag**: `10` (2 bits)
*   **diff green (dg)**: Green difference biased by 32 (6 bits, range `-32` to `+31`).
*   **dr - dg**: Red difference minus green difference biased by 8 (4 bits, range `-8` to `+7`).
*   **db - dg**: Blue difference minus green difference biased by 8 (4 bits, range `-8` to `+7`).
*   **Byte Range (Byte 1)**: `0x80` - `0xBF`

### 4. `OPPS_RUN` Chunk (1 byte)
Used when the current pixel is identical to the previous pixel.

```
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 1 │ 1 │      Run Length       │
└───┴───┴───┴───┴───┴───┴───┴───┘
```
*   **Tag**: `11` (2 bits)
*   **Run Length**: Run length biased by -1 (6 bits, range `1` to `62` stored as `0` to `61`).
*   **Byte Range**: `0xC0` - `0xFD`
*   *Note*: The run lengths `63` and `64` are not supported to avoid collisions with the `OPPS_RGB` and `OPPS_RGBA` tags. Runs larger than 62 must be split into multiple chunks.

### 5. `OPPS_RGB` Chunk (4 bytes)
Used when the alpha value matches the previous pixel but the differences cannot be encoded with `OPPS_DIFF` or `OPPS_LUMA`, and the pixel does not exist in the running palette.

```
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 1 │ 1 │ 1 │ 1 │ 1 │ 1 │ 1 │ 0 │  (0xFE)
├───┴───┴───┴───┴───┴───┴───┴───┤
│           Red Value           │  (8 bits)
├───┴───┴───┴───┴───┴───┴───┴───┤
│          Green Value          │  (8 bits)
├───┴───┴───┴───┴───┴───┴───┴───┤
│          Blue Value           │  (8 bits)
└───────────────────────────────┘
```
*   **Tag**: `0xFE` (8 bits)
*   **Red, Green, Blue**: Raw channel values.

### 6. `OPPS_RGBA` Chunk (5 bytes)
Used when the alpha value of the current pixel differs from the previous pixel, and the pixel does not exist in the running palette.

```
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 1 │ 1 │ 1 │ 1 │ 1 │ 1 │ 1 │ 1 │  (0xFF)
├───┴───┴───┴───┴───┴───┴───┴───┤
│           Red Value           │  (8 bits)
├───┴───┴───┴───┴───┴───┴───┴───┤
│          Green Value          │  (8 bits)
├───┴───┴───┴───┴───┴───┴───┴───┤
│          Blue Value           │  (8 bits)
├───┴───┴───┴───┴───┴───┴───┴───┤
│          Alpha Value          │  (8 bits)
└───────────────────────────────┘
```
*   **Tag**: `0xFF` (8 bits)
*   **Red, Green, Blue, Alpha**: Raw channel values.

---

## End Marker

The stream is terminated with exactly 8 null bytes:
`0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00`

---

## Worked Encoding Example

Suppose we want to encode a 2x2 image of RGB pixels.
- Dimensions: Width = 2, Height = 2 (Channels = 3, Colorspace = 0, Flags = 0).
- Pixel values (R, G, B):
  1. Pixel 0: `(255, 0, 0)` - Red
  2. Pixel 1: `(255, 0, 0)` - Red (Same as previous)
  3. Pixel 2: `(254, 0, 1)` - Very close to Red
  4. Pixel 3: `(0, 255, 0)` - Green (large diff)

### Header Generation
- Magic: `OPPS` (`0x4F 0x50 0x50 0x53`)
- Width: 2 (`0x00 0x00 0x00 0x02`)
- Height: 2 (`0x00 0x00 0x00 0x02`)
- Channels: 3 (`0x03`)
- Colorspace: 0 (`0x00`)
- Flags: 0 (`0x00`)
**Total Header bytes**: `4F 50 50 53 00 00 00 02 00 00 00 02 03 00 00` (15 bytes)

### Pixel Encoding Steps (Previous Pixel initialized to `(0, 0, 0, 255)`)

#### 1. Pixel 0: `(255, 0, 0, 255)`
- Palette Index: `(255 * 3 + 0 * 5 + 0 * 7 + 255 * 11) % 64 = (765 + 2805) % 64 = 3570 % 64 = 50`.
- Running Palette at index 50 is currently `(0, 0, 0, 0)`. No match.
- Previous pixel is `(0, 0, 0, 255)`.
- Diffs: `dr = 255`, `dg = 0`, `db = 0`. Differences are too large for `DIFF` or `LUMA`.
- Alpha matches previous pixel (`255`).
- We write `OPPS_RGB`: `0xFE 0xFF 0x00 0x00`.
- Update previous pixel: `(255, 0, 0, 255)`.
- Update running palette: `palette[50] = (255, 0, 0, 255)`.

#### 2. Pixel 1: `(255, 0, 0, 255)`
- Same as previous pixel. We start a run.
- Since it's the last pixel in a run (or next is different), we'll encode it. Here, next pixel is different.
- Run length = 1.
- We encode `OPPS_RUN` with run length 1 (stored as `0`): `0xC0` (`0b11000000`).
- Update previous pixel: `(255, 0, 0, 255)`.

#### 3. Pixel 2: `(254, 0, 1, 255)`
- Palette Index: `(254 * 3 + 0 * 5 + 1 * 7 + 255 * 11) % 64 = (762 + 7 + 2805) % 64 = 3574 % 64 = 54`.
- Running Palette at 54 is `(0, 0, 0, 0)`. No match.
- Previous pixel is `(255, 0, 0, 255)`.
- Diffs: `dr = 254 - 255 = -1`, `dg = 0 - 0 = 0`, `db = 1 - 0 = 1`.
- Diffs are in range `[-2, 1]`.
- We encode as `OPPS_DIFF`:
  - `dr` biased: `-1 + 2 = 1` (`0b01`)
  - `dg` biased: `0 + 2 = 2` (`0b10`)
  - `db` biased: `1 + 2 = 3` (`0b11`)
  - Tag prefix: `0b01`
  - Byte: `0b01011011` = `0x5B`.
- Update previous pixel: `(254, 0, 1, 255)`.
- Update running palette: `palette[54] = (254, 0, 1, 255)`.

#### 4. Pixel 3: `(0, 255, 0, 255)`
- Palette Index: `(0 * 3 + 255 * 5 + 0 * 7 + 255 * 11) % 64 = (1275 + 2805) % 64 = 4080 % 64 = 48`.
- Running Palette at 48 is `(0, 0, 0, 0)`. No match.
- Previous pixel is `(254, 0, 1, 255)`.
- Diffs are too large.
- We encode as `OPPS_RGB`: `0xFE 0x00 0xFF 0x00`.
- Update previous pixel: `(0, 255, 0, 255)`.
- Update running palette: `palette[48] = (0, 255, 0, 255)`.

### End Marker
- Write 8 null bytes: `00 00 00 00 00 00 00 00`.
