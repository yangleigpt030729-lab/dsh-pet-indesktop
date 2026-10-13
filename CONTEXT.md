# Desktop Pet Experience

## Companion expression / speech / feeding increment (2026-10-13)

The single head-touch toggle belongs to Interaction → Click & Sound, using the existing default-off key. Shared click speech opts displayed head replies into the existing VoiceChimeService only; ordinary click may remain off. Receipt/permission generation/role/style/expiry checks guard queued synthesis. Child slots supply their own style, voice and file-reading authorization. A small expression adapter preserves character prompts and never uploads custom fixed phrases. File feeding accepts all supported metadata types silently; content-reading confirmation/progress takes precedence over statistics/fun speech. Decline resumes stats then delayed metadata-only AI; explicit accept keeps the independent content session per actor. No automatic reading of nontext input. Fake records original speech callbacks offline. See [increment report](docs/PR-REPORT-COMPANION-EXPRESSION-SPEECH-FEED-2026-10-13.md) and [Windows guide](docs/WINDOWS10-COMPANION-ACCEPTANCE.md).

## Companion integration (2026-10-13)

The existing Settings System owns proactive_chat and default-off companion_interaction preferences; no parallel settings manager. Ordinary proactive limits are 1..9999 daily / 1..99 minutes (defaults 10/30), with conservative opt-out migration of legacy 0/>99. Explicit reminders keep the existing TodoStore JSON and panel, durable receipt-based delivery within the original ten-minute grace, and one asynchronous disk worker. A visible head core consumes one completed click; ambiguous/body locations retain ordinary clicks, drag/probe/spin precedence stays intact. Touch/feed reuse ChatService in a single ephemeral interaction channel, never write chat sessions or memory; feed prompts contain only bounded safe type/count/size metadata. Manual chat wins. ModernSettingsDialog holds unique interaction rows and the screen-activity clear action retains its old JSON scope. Fake launcher injects isolated Providers and enables enhancements only for a new Fake directory. Same-user normal variant migration preserves SQLite WAL/quota and existing destinations; pending migration pauses ordinary proactive traffic. Native Win10 build/DeepSeek acceptance remains outstanding. See [complete delivery](docs/PR-REPORT-COMPANION-COMPLETE-2026-10-13.md) and [Windows guide](docs/WINDOWS10-COMPANION-ACCEPTANCE.md).


The user-facing desktop-pet experience shared by settings, menus, overlays, and
their platform-specific presentations.

## Language

**Shared UX Contract**:
The cross-platform agreement for information architecture, state semantics,
interaction meaning, spacing roles, and brand roles. Platform presentation may
vary without changing this contract.
_Avoid_: Pixel parity, identical native chrome

**Settings System**:
The single product surface that owns every persistent user preference. Legacy
settings may temporarily redirect into it but do not define a second contract.
_Avoid_: Modern settings, legacy settings

**Menu Action Model**:
The shared set of menu commands, canonical labels/icons, callbacks, capability
availability, and runtime enablement semantics, independent of platform
presentation.
_Avoid_: Modern menu behavior, legacy menu behavior

**Menu Layout Tree**:
A versioned tree of stable action IDs and one-level submenus. It owns order and
user visibility, explicit separators, and optional alias/icon presentation
overrides, while the Menu Action Model owns canonical presentation, callbacks,
runtime state, and platform capability. Missing actions from newer versioned
defaults are inserted beside their nearest template sibling; explicit hidden
nodes and user ordering remain authoritative.
_Avoid_: Serialized QAction, platform-specific menu order

**Menu Presentation Override**:
An optional Menu Layout Tree decoration. Aliases replace canonical labels only
at runtime while the editor retains the canonical label for orientation. Icon
overrides may select a semantic icon, suppress the icon, or reference a
validated local image with contain/cover rendering; an unreadable local image
falls back to the Menu Action Model icon.
_Avoid_: Renamed command, embedded image bytes

**Capability Unavailable**:
An action cannot exist on the current platform or build. The Menu Layout Tree
retains its position for cross-platform editing, while the current runtime may
omit it and the editor explains the capability reason.
_Avoid_: Disabled feature, hidden action

**Runtime Disabled**:
An action exists on the current platform but its owning feature is currently
off or has no configured content. It keeps its Menu Layout Tree position and is
rendered with a disabled style and explanation; changing the feature toggle
never rewrites or filters the tree.
_Avoid_: Capability unavailable, user-hidden

**Dock Recovery Menu**:
The native macOS Dock context menu that keeps core recovery actions, especially
opening the Settings System, reachable when the pet window is hidden or mouse
input passes through it.
_Avoid_: Pet context menu, tray menu

**Settings Popup Surface**:
The shared settings-menu presentation used by selectors and command buttons.
It owns popup anchoring, minimum trigger width, row geometry, disabled state,
submenu arrows, and trailing selection checks; callers only provide actions.
_Avoid_: Copied menu stylesheet, native button menu indicator

**Image Directory Preview**:
An on-demand right-side drawer for image-directory settings. It uses three
shortest-height columns, preserves each thumbnail's useful aspect ratio, labels
every card with an elided filename and full-name tooltip, and defers directory
scanning and image decoding until the user presses Preview.
_Avoid_: Inline settings grid, eager gallery

**Settings Capability Domain**:
A stable sidebar destination organized by user intent. Every persistent setting
has one owning domain; platform support changes availability, not ownership.
_Avoid_: Module page, Windows settings page

**Report Gate**:
The single control for how much of one aggregated event class the pet reports.
It is a pass probability in `0.00–1.00` (`0.00` silences the class, `1.00`
reports every occurrence) and there is no boolean switch: the settings slider is
the only fine-grained control, while the pet menu offers only the two endpoints.
A gate governs the bubble step alone — detectors and the raw-record chain are
never sampled — and it never covers the whole feature.
_Avoid_: Notification toggle, report percentage, global mute

**Gate Group**:
The collapsible settings block that collects every report gate with the
bubble-phrase rows of its own event class, so a gate sits next to what it
controls. It is expanded by default and auto-expands when a search matches a row
inside it.
_Avoid_: Hidden advanced panel, per-feature switch list

**Session-End Spawn Freeze**:
The process-wide latch armed when the operating system announces that the
session is ending (`WM_QUERYENDSESSION`/`WM_ENDSESSION`, or Qt's session
signals as a fallback). While armed, no child ffmpeg process may be spawned and
existing readers are stopped, because a process created inside a tearing-down
Windows session fails DLL initialization (0xc0000142) and blocks shutdown.
The freeze is one-way: a process that survives a cancelled shutdown stays
frozen rather than resuming animation.
_Avoid_: Shutdown option, ffmpeg kill switch

**Local Long-Term Memory**:
User-authorized facts stored in SQLite below the existing user data directory,
shared by sessions and characters in that directory. Reading and automatic
extraction have separate, default-off consent switches in AI 与对话. Disabling
reading prevents database access in chat requests; explicit management remains
available. Memory records are quoted data, never model-generated user facts or
instructions. Deleting memory and deleting chat history are separate actions.
_Avoid_: Chat history summary, inferred user profile

**Proactive Companion Chat**:
An optional process-level AppShell service that reuses the chat Provider and
character prompt, generates short ordinary text bubbles, and never saves its
synthetic task or model output into user sessions or long-term memory. Upgrades
remain opt-out. All ordinary categories share a persisted maximum of ten
successful presentations per local day and at least thirty minutes between
presentations; paid attempts have a separate bounded budget. SQLite and model
work stay off the GUI thread. A crash during the UI/SQLite handoff holds an
ambiguous reservation conservatively. Explicit Todo delivery is independent;
P2-C durable outbox and catchup are NOT IMPLEMENTED.
_Avoid_: Proactive screen recognition, inferred scheduled tasks, proactive TTS

Proactive presentation receipts include a new accepted text generation, rather
than an old widget visibility check. Proactive SQLite v2 binds settlement to its
reserved local day, quota, spacing and short presentation window. Uncertain
crash timing survives midnight cleanup. Recent model prompts contain only fixed
semantic labels; prior utterance wording stays local even when memory consent
was previously enabled. Windows acceptance uses an isolated source test directory
and does not ship credentials or pretend a Linux build is a Windows EXE.

Windows user evidence (2026-10-13): Win10 22H2 x64 / Python 3.12 x64 with
the companion constraints starts the GUI and renders proactive settings; the
island settings entry works. The original overlay right-click settings silently
returned when process isolation was disabled; it now reuses the same primary
PetInstance dialog and supplies per-slot in-process fallbacks. Settings children
carry a custom Config base and, only for Fake acceptance, an explicit Fake flag.
Deferred presentation timers are bound to the dialog lifetime. The default
acceptance launcher explicitly injects separate Fake Providers into manual and
proactive services, preserving the live credential checks. A temporary user
injection already displayed a native Windows synthetic bubble; formal fixes,
complete Windows acceptance and real DeepSeek remain pending. See
docs/PR-REPORT-COMPANION-WINDOWS-ENTRIES-2026-10-13.md.
