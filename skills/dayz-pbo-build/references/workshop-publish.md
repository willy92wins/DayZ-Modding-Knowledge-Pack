# Publishing a signed mod to the Steam Workshop (DayZ, appid 221100)

Measured on 2026-11-12 and 2026-11-19 on one Windows PC with the Steam client
signed in: signing a released PBO, what a server with `verifySignatures = 2`
does with it, creating a hidden Workshop item with SteamCMD, what a SteamCMD
login does to the Steam client on the same machine, updating the item with the
Publisher, and the owner's subscribed copy of that private item. An update
with SteamCMD, an update reaching a subscriber, the `!Workshop` junction and
`meta.cpp` were **not** measured.

## The item folder

    addons\<Mod>.pbo
    addons\<Mod>.pbo.<authority>.bisign
    keys\<authority>.bikey
    mod.cpp

The `.biprivatekey` never goes into the item or the repository.

[EXACT][CLAIM-WORKSHOP-SIGN-DSUTILS] Signing with the DsUtils of DayZ Tools
(`Bin\DsUtils`): `DSCreateKey <authority>` writes the key pair,
`DSSignFile <authority>.biprivatekey <Mod>.pbo` writes the `.bisign` beside the
PBO, and `DSCheckSignatures <addons folder> <keys folder>` printed
`Signature ... is OK`. The `.bisign` is a separate file: the PBO had the same
sha256 before and after signing. The three tools write `.RPT` and `.mdmp`
files next to their own executable, so run a copy of them from a folder of
your own.

[EXACT][CLAIM-WORKSHOP-SIGN-SERVER-CHECK] A retail DayZServer 1.30.164289.70,
started with `-config` on a copy of its stock `serverDZ.cfg` (which has
`verifySignatures = 2`) with `BattlEye = 0` added, loaded the signed mod with
`-mod`, and a retail client loaded the same mod folder. With the item's
`.bikey` missing from the server's `keys` folder, the server kicked the client
0.14 s after it entered `AuthPlayerLoginState`: its RPT logged
`kicked from server: 120` with a message, in that machine's language, saying
that the client has a PBO the server does not have, and the client logged
`Error thrown: 0x00040078`. The message does not mention signatures.
With the `.bikey` copied into `keys` and nothing else changed, the client
passed `AuthPlayerLoginState` and the server logged `is connected`. In that
second run BattlEye kicked the client 23 s after it joined, with
`Game restart required` (kick 240), although the client ran without BattlEye;
the server had copied `BEServer_x64.dll` to its profile. Why was not
investigated.

[INFERRED] So a join test that has to last longer needs a client with
BattlEye, or a server shown to run without it: the logs do not say whether the
server applied `BattlEye = 0`. Neither was tried.

## Two ways to publish

| | Publisher (DayZ Tools) | SteamCMD |
|---|---|---|
| Session | The running Steam client's (inferred from its files) | Its own login with an account |
| Command line | None found: no `PublisherCmd`, and no option in the Publisher's strings | `+workshop_build_item <vdf>` |
| On a machine where people play | No log off in the client's log in three publications (below) | A login with the client's account kicked the Steam client off (below) |

[EXACT][CLAIM-WORKSHOP-PUBLISHER-FILES] `Bin\Publisher\Publisher.exe`
(file version 1.0.240.639, signed by Bohemia Interactive) is a 32-bit WPF
application that reaches Steam through `steam_api.dll`, with
`steam_appid.txt` = 221100. Its strings include `SteamAPI_Init`,
`IsSteamRunning` and "Publisher requires that the Steam client is online".
DayZ Tools ships no `PublisherCmd` (the command-line publisher of Arma 3
Tools), and no command-line option shows in the Publisher's strings. This was
read from the installed files without running them.

[INFERRED] From those strings, the Publisher publishes with the session of the
running client instead of logging in. Not measured directly; what it left in
that client's logs is below.

### Updating an item with the Publisher

[EXACT][CLAIM-WORKSHOP-PUBLISHER-UPDATE] Updating an existing private item
with the Publisher while the Steam client was running: its content folder is
the item's root, the folder that holds `addons` and `keys`. Given the `addons`
folder instead, it copied only the PBO and its `.bisign` to the root of its
temporary folder and failed before uploading: `Bin\Logs\dayzpublisher.rpt`
logged `System.IO.DirectoryNotFoundException` for `...\Addons` in
`UpdateMetadataOuter`. Given the root folder, its log went `Start`, the copy
to `%TEMP%\!Publisher_<title>_<guid>`, `Processing tags`,
`Steam Workshop item id is set, the item will be update`,
`Publishing to Steam Workshop...` and `Clean up` 5.7 s later (14 to 16 s for a
large mod), and the client's `logs\workshop_log.txt` recorded
`Upload starting`, `Uploaded new content` with a new manifest id, a new
preview file and `Upload finished ... : OK`. The chosen visibility shows in
neither log; the Publisher's files offer public, friends only and private, and
no unlisted. In three publications with the client running (this update and
two of another item on 2026-11-12), the client's `logs\connection_log.txt`
had no line during the publication, no log off and no `Session Replaced`.

### The owner's copy of a private item

[EXACT][CLAIM-WORKSHOP-PRIVATE-SUBSCRIBED-COPY] Subscribed from the owner's
account, the private item downloaded in about 2 s to
`steamapps\workshop\content\221100\<id>`, with the same files and sha256 as
the item folder. Days later the client removed it twice (in between it had
added it back by itself and downloaded it in 2 s), each time logging
`Get details for item <id> failed : Access Denied` and then
`Detected workshop change : removing unknown item <id>` in
`workshop_log.txt`. After the Publisher update above, while the owner said
they were subscribed, two watches of 7 and 40 minutes within the next two
hours found no line naming the item in `workshop_log.txt` besides the
upload's, and no entry for it in `appworkshop_221100.acf`.

[INFERRED] On the owner's own client a private item is no stand-in for a
public one: measure an update reaching subscribers on a public item.

## SteamCMD

### Before any SteamCMD login on a machine where people play

[EXACT][CLAIM-WORKSHOP-STEAMCMD-SESSION-REPLACED] A manual SteamCMD login (the
owner typing `login <account>`) with the account that the Steam client had
signed in on the same machine replaced the client's session. In the same
second as SteamCMD's `LogOnResponse` OK, the client's
`logs\connection_log.txt` recorded `RecvMsgClientLoggedOff('Session Replaced')`
and `not auto reconnecting due to Session Replaced`. The client did not
reconnect by itself: the owner restarted it 44 minutes later, and it logged on
again 2 minutes after that. Meanwhile, the other test runs on that machine
reported kick 49 in `WaitAuthPlayerLoginState` on the joins they tried.
`HKCU\Software\Valve\Steam\ActiveProcess` did not change, so a registry
check misses it; the client's `connection_log.txt` shows it.

So, on a machine where people play: publish with the Publisher, or run
SteamCMD with that account only while the Steam client is closed and no game
is running, the first login included. A second account was not tried.

[INFERRED] Any SteamCMD login with that account does the same, an unattended
one from the cached session and `workshop_download_item` included. Not
measured: the cached login below ran with the client already offline.

### Login

[EXACT][CLAIM-WORKSHOP-STEAMCMD-LOGIN] Download
`https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip` and check that
`Get-AuthenticodeSignature steamcmd.exe` reports `Valid` with a Valve signer
before running it. The first run updates itself (about 43 MB) and relaunches,
and the relaunched process lost a `+quit` given on the command line, so do the
first run by hand. The login is the account owner's, once: `login <account>`
and the password; the first attempt answered `Account Logon Denied` and asked
for the Steam Guard code; then `quit`. After that an unattended run logged in
from the cached session in about one second, with `steamcmd +runscript <file>`
and this file:

    @NoPromptForPassword 1
    @ShutdownOnFailedCommand 1
    login <account>
    workshop_build_item "<path to the .vdf>"
    quit

With these two settings that run logged in from the cached session and exited
by itself; an unattended run without a cached session, or with a failing
command, was not tried. SteamCMD writes the account name and the SteamID in
its own logs.

### Creating a hidden item

[EXACT][CLAIM-WORKSHOP-STEAMCMD-CREATE] Creating a hidden DayZ item:

    "workshopitem"
    {
        "appid"           "221100"
        "publishedfileid" "0"
        "contentfolder"   "C:\\path\\to\\item"
        "visibility"      "2"
        "title"           "..."
        "description"     "..."
        "changenote"      "..."
    }

`publishedfileid` 0 creates the item, and SteamCMD writes the new id back into
the `.vdf`. The run printed `Create new workshop item ( PublishFileID <id>)`,
`Uploading content...`, `Committing update...` and `Success.` in 13 s, with no
`previewfile` and no Workshop legal-agreement warning for that private item.
`visibility` takes the Steamworks values 0 public, 1 friends only, 2 private
and 3 unlisted; only 2 was used. Updating an item with SteamCMD was not
measured; the update measured here went through the Publisher (above).
