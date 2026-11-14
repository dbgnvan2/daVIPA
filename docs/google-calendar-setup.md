# Google Calendar Integration Setup

daVIPA can create Google Calendar events directly from action items, making it easy to schedule meetings and block time for tasks.

## Features

- 📅 Create calendar events from action items
- 🔗 Automatic linking of calendar events to tasks
- ⏰ Set start time, duration, location, and attendees
- 🌍 **Automatic timezone detection** - uses your local timezone
- 📝 Pre-fill event with action item details
- 🔄 Events appear as links in the item editor
- ✅ **Meeting tracking** - automatically marks items as meetings with scheduled time
- ⤴ **Export a planned day** - push the Plan screen's time blocks for one date out as timed events, and re-export the same day without duplicating anything
- ↻ **Read meetings into the Plan** - draw one day's calendar events on the Plan grid so no block is planned over them

## Configuration Directory

daVIPA stores Google Calendar credentials and authentication tokens in:
```
~/.getmoredone/
```

This is your **home directory**, not the project directory. This approach:
- ✅ Keeps credentials secure (less likely to commit to git)
- ✅ Persists across project clones/deletions
- ✅ Shares credentials across multiple daVIPA projects
- ✅ Follows standard patterns (like ~/.ssh, ~/.aws)

**Files stored:**
- `credentials.json` - OAuth client credentials (you provide this)
- `token.pickle` - Your authentication token (auto-generated on first login)

Both files are sensitive and should be kept private.

## Prerequisites

1. Python packages (already in requirements.txt):
   - google-auth
   - google-auth-oauthlib
   - google-auth-httplib2
   - google-api-python-client
   - tzlocal (for automatic timezone detection)

2. Google Cloud Project with Calendar API enabled
3. OAuth 2.0 credentials

## Setup Instructions

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. In the project, go to **"APIs & Services" > "Library"**
4. Search for **"Google Calendar API"**
5. Click **"Enable"**

### Step 2: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services" > "Credentials"**
2. Click **"+ CREATE CREDENTIALS"** > **"OAuth client ID"**
3. If prompted, configure the OAuth consent screen:
   - Choose **"Internal"** (for organization) or **"External"** (for personal use)
   - Fill in required fields:
     - App name: "daVIPA"
     - User support email: your email
     - Developer contact: your email
   - Click **"Save and Continue"**
   - On Scopes, click **"Add or Remove Scopes"**
   - Search for "Google Calendar API" and select: `.../auth/calendar`
   - Click **"Save and Continue"**
   - On Test users (if External), add your email
   - Click **"Save and Continue"**

4. Back on Credentials page:
   - Click **"+ CREATE CREDENTIALS"** > **"OAuth client ID"**
   - Application type: **"Desktop app"**
   - Name: "daVIPA Desktop"
   - Click **"Create"**

5. Download the credentials:
   - Click the download icon next to your OAuth 2.0 Client ID
   - This downloads a JSON file (usually named like `client_secret_XXXXX.json`)

### Step 3: Install Credentials

1. Rename the downloaded file to `credentials.json`
2. Place it in the daVIPA config directory:
   ```bash
   mkdir -p ~/.getmoredone
   mv ~/Downloads/client_secret_*.json ~/.getmoredone/credentials.json
   ```

3. Set correct permissions:
   ```bash
   chmod 600 ~/.getmoredone/credentials.json
   ```

### Step 4: First-Time Authorization

1. Launch daVIPA
2. Open any action item
3. Click the **"📅 Calendar"** button
4. Fill in event details
5. Click **"Create Calendar Event"**
6. Your browser will open asking you to authorize the app
7. Sign in with your Google account
8. Click **"Allow"** to grant calendar access
9. The browser will show "The authentication flow has completed"
10. Close the browser tab and return to daVIPA

A `token.pickle` file will be created in `~/.getmoredone/` to save your authorization for future use.

## Usage

### Creating a Calendar Event

1. **Open an action item** in the Item Editor
2. Click the **"📅 Calendar"** button (purple, on the button bar)
3. Fill in the event details:
   - **Event Title**: Defaults to action item title
   - **Date**: Use quick buttons (Today, +1) or enter YYYY-MM-DD
   - **Start Time**: Hour (1-12), Minute (0-59), AM/PM (uses your local timezone)
   - **Duration**: In minutes (default: 60)
   - **Description**: Optional (defaults to action item description)
   - **Location**: Optional
   - **Attendees**: Optional, comma-separated emails
4. Click **"Create Calendar Event"**
5. The event is created and automatically:
   - A link appears in the item's Links section
   - **"Is Meeting"** checkbox is checked
   - **"Meeting Time"** field displays the scheduled time

### Viewing Calendar Events

- Calendar links appear in the **Links & Notes** tab of the item editor
- Labeled as "Calendar: [Event Title]"
- Click the link to open the event in Google Calendar (browser)

### Managing Events

- **Edit**: Click the calendar link to open in Google Calendar, edit there
- **Delete**: Delete from Google Calendar directly
- **Remove Link**: Click the 🗑️ button next to the link in daVIPA

### Exporting a Planned Day

The Plan screen's **"⤴ Google Calendar"** button (in the header, between
**⚙ Day Settings** and **+ Break**) writes the day you are looking at to your
calendar as timed events.

1. Open the **Plan** screen and pick the date.
2. Build the day: item blocks, buffers and breaks, placed on the grid.
3. Click **"⤴ Google Calendar"**.

The button disables itself while the export runs and the status line reports
the result, for example:

```
3 of 5 block(s) exported to Google Calendar for 2026-11-12 — 2 new, 1 updated, 2 skipped (not on the grid)
```

**What is exported**

- Every block placed on the grid that has a length: item blocks, buffers and
  breaks alike.
- The event title is the title the Plan screen draws on the block — the action
  item's title for an item block, the block's own label (or "Buffer" / "Break")
  otherwise.
- The event description is the item's **Next action** when it has one,
  followed by the line `Planned in daVIPA.`
- Times are the block's own start time and planned minutes, in your local
  timezone.

**What is not exported, and why**

- **Blocks not on the grid.** Anything under "Outside the day" has no box, so
  the app does not know when it happens. Writing it at whatever clock string
  its row carries would put work on your calendar at a time nobody chose.
  These are counted in the status line as "skipped (not on the grid)".
- **Blocks with no length** ("skipped (no length)") and blocks whose stored
  time cannot be read ("skipped (unreadable time)").
- **Lunch.** Lunch is a gap in the grid rather than a time block, so there is
  nothing to write. Block it out in Google Calendar directly if you want it
  there.
- **The rest of the Plan screen.** Only time blocks for the selected date are
  exported — not the week, not the item list, nothing from Vision/Strategy/Plan.

**What a second export of the same day does**

Nothing is duplicated. Each block records the id of the event it owns, and
every event daVIPA writes also carries that block's id in its own private
properties. On a re-export:

- a block whose event still exists has that event **updated** in place, so a
  block you moved or resized moves and resizes on the calendar;
- a block whose event you deleted by hand in Google Calendar is
  **re-created** ("1 re-created");
- an event whose block you have since deleted in daVIPA is **removed**
  ("1 removed");
- an event **without** daVIPA's marker is never touched. Your real meetings
  are safe, including ones in the same hour.

A block that failed or was skipped keeps its event: nothing is removed on the
strength of a run that did not confirm what the day holds.

Exporting a day you have **cleared** is worth doing for this reason: with no
blocks left there is nothing to send, but the events that day had still need
taking off the calendar, and the export says so — *"No blocks planned for
2026-11-12 — 2 removed"*. A day that never had anything exported reads
*"Nothing to export"* instead.

**Which calendar**

Your primary calendar, unless `plan_export_calendar_id` in the app settings
names another one. There is no control for it yet — it is read from the
settings file.

If you change it, the next export **moves** the events it had already made:
each block records the calendar its event is on, so the export takes the event
off the old calendar before creating it on the new one, and says so — *"3 of 3
block(s) exported … 3 moved to this calendar"*. Blocks you had never exported
are simply created on the new calendar. If a move cannot complete — the old
calendar is unreachable, say — that block is reported as failed and keeps its
old event, so running the export again finishes the job rather than leaving two
events for one block.

### Reading Meetings into the Plan

The Plan screen's **↻ Calendar** button reads the selected day from the
calendars in `plan_commitment_calendar_ids` (a list in the settings file;
default `["primary"]`) and draws each event in the boxes it covers. No block
can then be placed in those boxes. In the Plan's **Week** view the same
button reads the seven dates shown in one call. The full behaviour is in
`docs/USER_GUIDE.md`, under *Plan (Time Blocks)*.

- It uses the same credentials and token as the export, and the same
  `calendar` scope; nothing new has to be authorised.
- It never opens a browser to sign in. If the token has lapsed it says so —
  *"Google Calendar is set up but not connected yet"* — and you sign in from an
  item's *Add to Calendar* dialog, as for the export.
- Times are converted to this computer's time zone once, when read.
- Declined, cancelled and *free* events are left out, as are the events the
  export made, and each is counted on the status line.
- A calendar in the list that you can no longer see (removed, or shared access
  revoked) is skipped; the others are still read. The meetings already known
  from it stay, and the line above the grid names it until it can be read
  again. If none can be read, nothing is replaced and the failure is shown.
- List your own calendar first. A meeting on two listed calendars is taken
  from the first one, because whether you declined it, and whether you can
  change it, is recorded per calendar.
- **Changing a meeting from the Plan** (moving it, changing its length or
  title, deleting it) writes to the calendar the meeting was read from, through
  the same token. Only a meeting you organised, or one whose guests may change
  it, can be changed. Google emails the other guests only if you answer *Yes*
  when asked; the Plan day export never emails anyone. Before each write the
  event is read again, and if it changed in Google since it was last read,
  nothing is written.
- What was read is kept in the app's database, so the Plan opens without
  waiting on Google. When credentials and a token are present, a day not read
  in the last `plan_commitment_stale_minutes` (default 15) is read once in the
  background when you open it.

## Troubleshooting

### "Google Calendar libraries not installed"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

**If using a virtual environment (venv)**, make sure to activate it first:
```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Then install
pip install -r requirements.txt
```

**Or use the startup script** (recommended):
```bash
./start.sh  # Linux/Mac
start.bat   # Windows
```

### "Google Calendar is set up but not connected yet"

The export says this when `credentials.json` is in place but
`~/.getmoredone/token.pickle` is not — the file written the first time you
authorise daVIPA in a browser.

**Solution**: connect once from an item's **Add to Calendar** dialog (open an
item, Add to Calendar), which can open the browser and complete Google's
consent screen. Then export the day.

The export refuses rather than doing this itself on purpose: it runs on a
background thread so the app stays usable, and the consent flow waits on a
browser window with no time limit. Started from there it would leave the Plan
screen's button disabled with no way back.

### "Google Calendar credentials not found"

**Solution**: Make sure `credentials.json` is at `~/.getmoredone/credentials.json`

### "Invalid date format"

**Solution**: Use YYYY-MM-DD format (e.g., 2026-01-15)

### "Invalid time"

**Solution**: Hour must be 1-12, Minute must be 0-59

### "Failed to create calendar event: 403"

**Solution**:
1. Verify Google Calendar API is enabled in Google Cloud Console
2. Check OAuth consent screen status
3. Make sure your email is in test users (if External app)
4. Try deleting `~/.getmoredone/token.pickle` and re-authorizing

### "Authentication flow has completed" but event not created

**Solution**:
1. Check terminal output for errors
2. Verify `token.pickle` was created at `~/.getmoredone/token.pickle`
3. Try the calendar creation again

### Authorization browser doesn't open

**Solution**:
1. Look for a URL in the terminal output
2. Copy and paste it into your browser manually
3. Complete authorization and return to app

### Calendar event appears at wrong time

**This should not happen anymore** - daVIPA now auto-detects your timezone.

If you still see incorrect times:
1. Verify your system timezone is set correctly
2. Restart daVIPA to pick up timezone changes
3. Check if `tzlocal` is installed: `pip show tzlocal`
4. If issue persists, check the terminal for timezone detection warnings

### Plan export says "Google Calendar needs you to sign in again"

The token file is there but cannot be used: access was revoked in your Google
account, the password changed, or the file is damaged. Signing in needs a
browser, and the export runs in the background where it cannot open one — so it
stops and says this rather than hanging. Use **Connect Google Calendar** from
the calendar dialog, which can open a browser, and then export again.

### Plan export says "2026-11-12 is already being exported"

An export of that day is still running — in this window or another one. One
export per day at a time, because two at once would race over the same events.
Wait for the status line to report, then click again.

### Plan export says "FAILED"

The status line names the first failure. One block failing is one block
failing — the rest of the day still goes out, and the export can be run again.
Transient Google errors (rate limits, 5xx) are already tried three times in
all — the first attempt and two retries, with backoff — before they are
reported, so a reported failure is a real one:
check the message, fix what it names, and click the button again.

## Security Notes

- **credentials.json**: Contains OAuth client credentials, keep private
- **token.pickle**: Contains your authorization token, keep private
- Both files are stored in `~/.getmoredone/` (user's home directory)
- Never commit these files to version control
- The `.gitignore` already excludes these files

## Timezone Handling

**Automatic Detection:**
daVIPA automatically detects and uses your **local timezone** when creating calendar events. No configuration needed!

- Uses the `tzlocal` library to detect your system's timezone
- Events are created in your local timezone automatically
- No more timezone confusion or manual configuration
- Falls back to UTC if timezone detection fails (rare)

**Example:**
- If you're in California (Pacific Time), events use `America/Los_Angeles`
- If you're in London, events use `Europe/London`
- If you're in Tokyo, events use `Asia/Tokyo`

This ensures calendar events appear at the correct time in Google Calendar, regardless of where you are.

## Privacy

- daVIPA accesses one calendar: your primary one, or the one
  `plan_export_calendar_id` names in app settings if you have set it. The
  OAuth scope it asks for covers your whole calendar account, which is what
  Google offers; the app only ever reads and writes the one calendar
- It only creates/reads events you explicitly create through the app
- A Plan export only ever updates or removes events daVIPA itself created, identified by a private property on the event; events it did not create are never modified or deleted
- No data is sent to external servers (direct Google API connection)
- Authorization tokens are stored locally on your machine

## Technical Details

- **API**: Google Calendar API v3
- **Authentication**: OAuth 2.0 (Desktop app flow)
- **Scopes**: `https://www.googleapis.com/auth/calendar`
- **Storage**: SQLite (links, meeting data), Local files (credentials/tokens)
- **Link Type**: `google_calendar` (stored in `item_links` table)
- **Timezone**: Auto-detected using `tzlocal` library
- **Plan export**: `src/getmoredone/calendar_exporter.py` (GUI-free), driven from `screens/plan.py`
  - `time_blocks.calendar_event_id` (TEXT) holds the event a block owns
  - Event markers: `extendedProperties.private.gmd_block_id` and `gmd_block_date`
  - Re-export finds the day's own events with `privateExtendedProperty=gmd_block_date=<date>`
  - Target calendar: `plan_export_calendar_id` in app settings (default `primary`)
  - Every Google call is timeout-bounded and retries 429/500/502/503/504 — and
    a 403 whose body gives a rate-limit reason — with exponential backoff
  - Each event is created with an id the app chooses, so a retried create
    cannot leave a second event behind
  - Exported blocks ask for your calendar's own reminder setting rather than
    carrying a popup of their own
- **Meeting Tracking**:
  - `is_meeting` flag in `action_items` table (INTEGER, 0 or 1)
  - `meeting_start_time` in `action_items` table (TEXT, ISO datetime format)

## Uninstalling

To remove Google Calendar integration:

```bash
# Remove credentials and tokens
rm ~/.getmoredone/credentials.json
rm ~/.getmoredone/token.pickle

# Revoke app access (optional)
# Go to: https://myaccount.google.com/permissions
# Find "daVIPA" and click "Remove Access"
```
