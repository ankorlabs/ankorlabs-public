# Turf Pong: daily video instructions for an AI agent

Your job: once a day, make one new Turf Pong video and post it as an Instagram Reel.

Turf Pong is a self-playing game. Coloured teams bounce balls around a board, take each other's tiles and grab power-ups. The first team to own 85% of the board wins. Each video is one complete game, with sound, in Reels format (1080×1920, 9:16, MP4, H.264 + AAC).

## 1. Make the video

There are two ways to do this. Use whichever one your tools support.

### Option A: run the script (needs Python 3 and Google Chrome, nothing to install)

```bash
curl -fsSLO https://ankorlabs.com/turf-pong-agent/make_video.py
python3 make_video.py --teams 2 --seed 2026-11-12 --out turf-pong-2026-11-12.mp4
```

The last line it prints is JSON:

```json
{"ok": true, "file": "/abs/path/turf-pong-2026-11-12.mp4", "winner": "Sky", "winnerShare": 88,
 "teams": [{"name": "Butter", "share": 13}, {"name": "Sky", "share": 88}],
 "seed": "2026-11-12", "seconds": 61.4, "hasSound": true, "finished": true, "bytes": 9214300}
```

If `ok` is false, it prints `{"ok": false, "error": "..."}` and exits with a non-zero code. Retry once. If it fails again, report the error instead of posting.

Options:

| Option | Values | Default | Meaning |
|---|---|---|---|
| `--teams` | 2, 3, 4 | 2 | Number of teams |
| `--seed` | any text | today's date | The same seed always gives the same game |
| `--speed` | 1, 2, 4 | 1 | 1 gives a game of about a minute |
| `--no-powerups` | flag | off | Plain game with no power-ups |
| `--out` | path | `turf-pong-<seed>.mp4` | Where to save the file |
| `--timeout` | seconds | 900 | How long to wait before giving up |

A video usually takes 15–60 seconds to make.

### Option B: use a browser (for agents that control Chrome)

Open this address in Chrome or Edge on a computer:

```
https://ankorlabs.com/turf-pong.html?agent=1&teams=2&seed=2026-11-12
```

The page makes the video on its own and saves it to the Downloads folder as `turf-pong-<seed>.mp4`. When the tab title changes to `TURF-PONG-DONE`, the video is finished. `TURF-PONG-FAILED` means it failed. The details, including the base64 MP4, are in `<script id="agent-result" type="application/json">`.

From code running in the page, you can also call:

```js
const r = await window.TurfPong.makeVideo({ teams: 2, speed: 1, seed: "2026-11-12" });
// r.mp4Base64, r.winner, r.teams, r.seconds, r.hasSound ...
```

## 2. Daily routine

1. **Seed:** use today's date (`YYYY-MM-DD`), so each day has one unique game.
2. **Teams:** vary the number of teams to keep the feed fresh. A simple rotation is 2 teams Monday to Thursday, 3 on Friday and Saturday, and 4 on Sunday.
3. **Check the result:** `ok` and `finished` should be true, and `seconds` should be between 20 and 180.
4. **Post it as a Reel** with a caption built from the result (see below).
5. **Don't** make extra videos to pick a "better" winner. Post the day's game as it is.

## 3. Caption template

```
Day {N} · {winner} takes the board in {seconds as m:ss} ⚪️
{team shares, e.g. Sky 88% · Butter 13%}
Who are you rooting for tomorrow? 👇
#turfpong #satisfying #simulation #pixelart #oddlysatisfying
```

- Team names are Butter (yellow), Sky (blue), Rose (red) and Peony (pink).
- Count {N} from the first day you posted.
- Keep the caption short. The video is the content.

## Notes

- The video has its own sound, so don't add music over it unless asked.
- The top and bottom of the frame are left empty on purpose, so Instagram's buttons and the caption don't cover the game.
- The game's page is https://ankorlabs.com/turf-pong.html.
