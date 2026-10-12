(* VoiceOver capture scaffold — cross-check for a11y_sr_transcript.
   Drives VoiceOver through a page in Safari and reads the Caption Panel
   (VO-F10), which renders spoken output as on-screen text.

   REQUIREMENTS (macOS 11+):
   - The host running this script needs Accessibility + Automation
     permissions (System Settings → Privacy & Security).
   - Safari must be allowed automation; VoiceOver enabled on demand.
   - Set a fixed VoiceOver speech rate first (VoiceOver Utility → Verbosity)
     so timing is reproducible.

   USAGE:
     osascript scripts/voiceover-capture.applescript "https://example.com" 12 out.jsonl
     # argv[1] = URL, argv[2] = number of VO+Right steps, argv[3] = output path

   Output: JSONL, one {step, text} per line. EXPERIMENTAL scaffold: human-
   driven cross-check, not a CI gate. Read docs/sr-crosscheck.md first. *)
on run argv
	set theURL to item 1 of argv
	set steps to (item 2 of argv) as integer
	set outPath to item 3 of argv

	-- 1. Open the page in Safari
	tell application "Safari"
		activate
		open location theURL
	end tell
	delay 4

	-- 2. Enable VoiceOver + Caption Panel (needs Accessibility permission)
	tell application "System Events"
		key code 96 using {command down, option down} -- Cmd+Option+F5: VoiceOver toggle
		delay 2
		key code 96 using {command down, option down} -- off again: ensure known state
		delay 1
		key code 96 using {command down, option down} -- on
		delay 2
		-- VO-F10 (Ctrl+Option+F10): Caption Panel on
		key code 109 using {control down, option down}
		delay 1
	end tell

	-- 3. Walk: initial announcement + N × VO+Right (Ctrl+Option+Right)
	set f to open for access outPath with write permission
	set eof of f to 0
	tell application "System Events"
		-- initial focus: VO reads the page top
		set txt to my captura()
		my escribe(f, 0, txt)
		repeat with i from 1 to steps
			key code 124 using {control down, option down} -- VO+Right
			delay 0.9
			set txt to my captura()
			my escribe(f, i, txt)
		end repeat
	end tell
	close access f

	-- 4. Restore: caption panel off, VoiceOver off
	tell application "System Events"
		key code 109 using {control down, option down}
		delay 1
		key code 96 using {command down, option down}
	end tell
	return "captured " & steps & " steps → " & outPath
end run

-- Read the Caption Panel text (AXStaticText descendants of the VO caption window)
on captura()
	tell application "System Events"
		try
			set txt to ""
			tell process "VoiceOver"
				set win to window "Caption Panel"
				repeat with e in (entire contents of win)
					if class of e is static text then set txt to txt & (value of e as text) & " "
				end repeat
			end tell
			return txt
		on error errMsg
			return ""
		end try
	end tell
end captura

-- Append a JSONL line {step, text}
on escribe(f, n, txt)
	set s to my reemplazar(txt, "\"", "\\\"")
	write "{\"step\":" & n & ",\"text\":\"" & s & "\"}" & linefeed to f
end escribe

on reemplazar(orig, viejo, nuevo)
	set AppleScript's text item delimiters to viejo
	set partes to text items of orig
	set AppleScript's text item delimiters to nuevo
	set res to partes as text
	set AppleScript's text item delimiters to ""
	return res
end reemplazar
