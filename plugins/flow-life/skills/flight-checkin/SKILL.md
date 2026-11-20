---
name: flight-checkin
description: Use when the owner asks to check in for a flight, or says an airline or booking site has not checked them in. Finds the booking in Gmail, takes the contact details from the folder, and does the airline's online check-in in the owner's Chrome, stopping only for passport or ID numbers (the owner types them) and for anything that costs money.
---

# flight-checkin: check the owner in for a flight

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Sensitive data; Sending, paying, signing)
first. Works best inside a flow-life folder (a `.agents/flow-life.toml` at or above it),
where the contact details live; outside one, take them from the booking mail.

The owner asking to be checked in **is** the go-ahead for that one check-in: submitting
the airline's check-in form for the flight they named (or the one next due). It is not a
go-ahead for anything that costs money, for another flight, or for another passenger.

## The one rule the owner set

**Do every step yourself.** The owner wants this automated. Each time you ask for
something the mail or the folder already holds (the email, the phone number, the booking
reference, which flight), you have failed them. Ask only for:

- **passport or ID numbers** (and their expiry or issuing country, if the form wants them
  on the same screen): the owner types these into the page themself. You never read them
  out of the identifiers file into a form, and never into chat;
- **anything that costs money**: a seat, a bag, priority, insurance. The answer is no
  unless the owner says otherwise;
- a genuine choice the mail cannot settle (two flights the same day, two passengers on
  one booking and the owner asked for only one).

Everything else (cookies, forms, dropdowns, ticks, Continue) is yours.

## Tools

- **Gmail** (the Gmail connector): thread search and reading.
- **Claude in Chrome** (`mcp__claude-in-chrome__*`): the owner's real Chrome, where they
  may already be signed in to the airline. Read the `anthropic-skills:chrome-browser`
  skill before the first step, load the browser tools in one ToolSearch call, and work in
  a new tab. Prefer `find` / `read_page` refs over screenshot coordinates; take a
  screenshot after each page change to see where you are.

If Gmail is not connected, ask the owner for the booking reference and surname only,
then carry on. If Claude in Chrome is not connected, say so in one line and stop: the
built-in browser has none of the owner's sign-ins and the airline will often block it.

## 1. Find the flight in Gmail

Search the last 60 days, newest first. Useful queries (combine with `newer_than:60d`):

- `subject:(booking OR itinerary OR "check-in" OR "check in" OR "boarding pass")`
- `from:(kiwi.com OR booking OR noreply)` together with an airline name the owner gave
- `"booking reference" OR "PNR" OR "reservation code"`

From the mail, take:

| Field | Where it usually is |
|---|---|
| Carrier and flight number | itinerary block, e.g. `XX 1234` |
| Date and departure time (local) | itinerary block |
| From / to airports | itinerary block |
| **Carrier PNR** | the airline's own 6-character code. An online travel agency (OTA) shows its own booking number too; the airline's site wants the **carrier** one, often listed per leg |
| Passenger name(s) | "Passengers" or "Travellers"; the surname as booked |
| Contact email and phone | an OTA confirmation's **"Your contacts"** section: what was used at booking |

**Which flight**: the one the owner named, else the next departure whose online check-in
is open now (most airlines open 24–72 h before departure and close 1–3 h before). A
booking with several legs on different carriers has a PNR per carrier: check in each leg
on its own carrier's site. Say which flight you picked in one line and carry on; do not
wait for a confirmation.

**An OTA that "checks you in automatically"** (Kiwi.com and similar) often fails silently
when the passport details were never sent to it. A mail saying check-in is pending, or
that it needs passenger details, means: do the airline's own check-in. Do not fill the
OTA's passport form unless the owner asks; the airline's site is quicker.

Read the mails; never reply to them, and do not file them unless the owner asks
(`/flow-life:file-email` does that).

## 2. Contact details: the folder first, then the mail

Look, in this order, and stop at the first that has both:

1. The folder's identifiers file (the profile's `identifiers`, default
   `personal-details.md`): rows labelled email, mobile or phone.
2. The folder's `CLAUDE.md` (a contact or travel section).
3. Claude's own memory, if it records the owner's contact details for travel forms.
4. The booking mail's "Your contacts" section.

**Never ask the owner for an email or phone the folder or the mail already has.** If none
of the four has a mobile number and the airline requires one, ask for it once, then offer
to add it to the identifiers file (a row, on a yes). Use the details in the form only: do
not repeat the phone number in chat or in your report.

Split a phone number into the country code and the national number (`+44 7700 900123` is
country `+44` / United Kingdom and `7700900123`, without the leading 0 of a national
format). Airlines' country dropdowns want the country chosen, not typed into the number
field.

## 3. Check in on the airline's site

Look up the airline in [references/airlines.md](references/airlines.md) first: where the
check-in starts, its steps, its traps. An airline that is not listed: start at its home
page and find "Check-in" in the top navigation (deep links to check-in pages break often),
then follow the generic steps below, and add what you learn to the file afterwards (see §5).

1. **Open the page** in a new tab. **Cookies**: decline non-essential ("Reject all",
   "Only necessary", "Manage → save without extras"). Never "Accept all".
2. **Find the booking**: the carrier PNR and the surname exactly as booked. If the site
   says the booking is not found, try the surname without diacritics, and check that the
   PNR is the carrier's and not the OTA's.
3. **Pick the passenger(s) and flight(s)**: the ones the owner asked for. A return flight
   that is not yet open is left for later.
4. **Contact details**: email, and the phone with the country dropdown set. Untick
   marketing and newsletter boxes.
5. **Passport / ID** (when asked; often not on a flight inside the Schengen area): **stop**.
   Tell the owner which page and which fields, in one line, and wait for them to say it is
   done. Fields that are not identifiers (nationality, date of birth, gender) you may fill
   from the identifiers file; the document number, its expiry and issuing country are the
   owner's to type.
6. **Seat**: keep the assigned seat when it is free. A seat map that pre-selects a paid
   seat, or a "choose your seat" step with a price, means: skip, "continue without
   choosing", "keep my free seat", or "random seat". Never confirm a seat with a price.
7. **Services and extras** (bags, priority, insurance, lounge, fast track, car hire):
   add nothing. Look for "Continue without", "No thanks", "Skip". If the only way forward
   adds something with a price, stop and ask.
8. **Conditions**: tick the conditions-of-carriage / dangerous-goods / terms box. This is
   part of the check-in the owner asked for; no extra yes is needed.
9. **Check in now** (or "Confirm", "Complete check-in"): click it. Before clicking, look
   once more at the page's total: it must be zero. If anything has a price, stop and ask.

A page that does something unexpected (a sign-in wall, a CAPTCHA, an error): a CAPTCHA
is the owner's to solve; a sign-in is the owner's (never type a password); an error is
retried once, then reported with what the page said.

## 4. Report

Short, in this order:

- **Checked in**: flight, date, departure time, from → to.
- **Seat**: the seat number, and whether it was the free assigned one.
- **Boarding passes**: on the confirmation page (and usually by mail, and in the airline's
  app). **Downloading or sending the boarding pass is the owner's click**; say where the
  button is. Do not download it.
- Anything left: another leg not yet open (and when it opens), a passport step the owner
  still has to do, an extra that was declined.

Never put the PNR, the phone number or a passport detail in the report beyond what the
owner needs to find the booking; "your booking with <airline>" is enough.

## 5. Afterwards

- A trait of the airline's site learned this run (a new URL, a step that moved, a trap) is
  a reusable fact: **propose** the line for
  [references/airlines.md](references/airlines.md) in the flow-life repository, written
  with no booking, name, number or date from this trip.
- If the folder keeps a process for this trip, offer to add one line to its README
  (`Checked in <date>, seat in the airline's app`) on a yes. No identifiers there.
- If the owner's contact details came from the mail and the folder had none, offer to add
  them to the identifiers file.

## Worked example (made up)

> Owner: check me in for Friday's flight.

1. Gmail, `newer_than:60d subject:(booking OR itinerary)`: an OTA confirmation with two
   legs. Leg 2 is `XX 1234`, Friday 07:05, carrier PNR `ABC12D`, passenger `A. Example`.
   A later OTA mail says automatic check-in failed: passenger details missing.
2. The identifiers file has an email row (`owner@example.com`) and a mobile row.
3. The airline is in `airlines.md`: start at its home page, Check-in in the top nav.
   Cookies: "Only necessary". PNR + `Example`. Contact: email, country United Kingdom,
   number. Seat 14C assigned free: kept. Services: continue without. Conditions ticked.
   Check in now. No passport asked (flight inside the Schengen area).
4. Report: "Checked in on XX 1234, Friday 07:05. Seat 14C (the free one). Boarding pass
   is on the confirmation page; the Download button is under the flight. Leg 1 is on
   another carrier and opens Thursday."
