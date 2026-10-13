# Desktop Pet Experience

## Speech lifecycle and focused fixes (2026-10-14)

User requests are now on a separate fix branch from 5556459, not an installer rebuild. Classic and modern chat headers share the Config display-name resolver and immediate in-process alias notifications without changing session IDs. Explicit interactions opt into SSE completion checks (length/EOF fallback) with a 256-token head-only budget; ordinary chat remains compatible. Default local chime quotes use time bands and deterministic day rotation, keeping user-language custom quotes and quote-off precedence. One revocable SpeechTicket binds an accepted text presentation to the original shared player/cache/channel, holds only automatic hide, preserves full-text paging, and releases on actual EndOfMedia or guarded failure/cancellation. Playback progress has no absolute 30-second duration cap; waiting and stalled playback have bounded release. Manual screen cues/results use active speech consent and captured actor/request identity, independent of automatic screen enablement or whitelist. No new persistent preference, persona/memory policy, dependency, animation or packaging change. Earlier native Windows behavior remains user-confirmed; this increment requires separate acceptance. See [report](docs/PR-REPORT-SPEECH-LIFECYCLE-2026-10-14.md) and [Windows source-only checklist](docs/WINDOWS10-SPEECH-LIFECYCLE-ACCEPTANCE.md).

## Installer v1.0.0 packaging (2026-10-14)

The user subsequently confirmed all ten Windows10 experience checks at 533eb1c, including real speech, shared hot volume/mute/settings synchronization, fast feeding, screen pre-cue/final reply and original island/auth/animation/drag. Packaging is the only new scope. The dedicated installer consumes the original root-EXE/_internal portable ZIP into a fresh directory, validates privacy/layout/PE/file hashes and retains existing frozen TTS/Qt/encoding gates. Fixed per-user AppId and LocalAppData Programs directory, no process force-close or user-data deletion, optional explicit migration of the existing variant Run value only. Original executable/business/dependencies and internal app version remain unchanged. Setup version1.0.0; native Setup NOT BUILT and installation/upgrade/uninstall NOT TESTED here. See [installer guide](docs/WINDOWS-INSTALLER-V1-ACCEPTANCE.md) and [report](docs/PR-REPORT-INSTALLER-V100-2026-10-14.md).

## Companion latency and volume (2026-10-13)

User-confirmed Win10 baseline now includes the Microsoft endpoint, island chat, fun feeding, explicitly authorized interpretation speech, final screen-reply speech and silent balance/statistics/progress. This increment adds active-category speech for actually displayed screen pre-cues, using existing MP3 cache without speculative online pre-generation. The real synthesis path no longer waits for voice-list refresh; optional metadata refresh is queued after success/GUI consent checks, single-flight, 2.5s timeout, six-hour success TTL and fifteen-minute failure throttle. Feeding starts after a leading 50ms bounded merge instead of two seconds, keeps single-flight/backoff/privacy and replaces silent statistics on actual reply. The one voice_chime_volume field controls the existing speech output, with default-false voice_chime_muted retaining the saved level. Menus/settings share event-driven bindings and targeted persistence; semantic disk fingerprints exclude only volume/mute/slot-ownership metadata, preserving role/task/privacy revocation without cancelling valid speech on volume changes. Original model, endpoint, chat, file authorization, animation and unrelated audio stay intact. The user has now confirmed these ten native Windows10 experience checks PASS; later installer validation is separate. See [report](docs/PR-REPORT-COMPANION-LATENCY-VOLUME-2026-10-13.md).

## Microsoft speech endpoint and accepted AI replies (2026-10-13)

The existing lazy Edge synthesis worker applies the project-owned api.msedgeservices.com WSS endpoint in memory, using the SDK trusted client token. Installed SDK files, proxy/TLS, cache and the shared player remain intact. Overlay island chat now reaches the existing OverlayShell quick-chat UI; Legacy and hidden-pet island chat retain their routes. Passive speech additionally accepts explicitly authorized file interpretation completions; active speech additionally accepts automatic screen AI replies independently of ordinary proactive-chat enablement. Both use exact display receipts and generation/feature/character/visibility guards; progress, statistics and failures stay silent; the screen pre-cue now opts into active speech as described above. Existing keys and default-off consent are unchanged. The user subsequently confirmed the product endpoint and these integration paths on Win10; later increments still require their own acceptance. See [delivery](docs/PR-REPORT-EDGE-TTS-ISLAND-RESULT-SPEECH-2026-10-13.md) and [Windows guide §12](docs/WINDOWS10-COMPANION-ACCEPTANCE.md).

## Windows FFmpeg console / build preflight (2026-10-13)

Runtime FFmpeg creation adds CREATE_NO_WINDOW on Windows while preserving all existing flags, priority, argv and stream/lifecycle behavior. Only imageio `_io` / `_utils` use a scoped subprocess proxy: stdlib convenience functions bind to that proxy, so metadata and cold version probes also enter the existing capture/Job Object funnel. Conversion joins the same Job; cold fps/exe/meta/thumbnail entries install the policy before spawning, and thumbnails honor session ending. Global subprocess/Popen inheritance stays intact. Official PowerShell scripts now carry UTF-8 BOM and run native ParseFile preflight before install/build and after source staging. User already built/runs the prior Python3.12/Qt6.8.3/PyInstaller6.19 portable on Win10 19045; this repair's native EXE/console/PowerShell5.1 results remain NOT TESTED here. See [report](docs/PR-REPORT-FFMPEG-NO-CONSOLE-2026-10-13.md) and [complete Windows workflow §11](docs/WINDOWS10-COMPANION-ACCEPTANCE.md#11-ffmpeg-黑窗口修复重新打包与原生复验).

## Independent accompaniment speech (2026-10-13)

Successful head/feed requests have no timed cooldown. Busy head gestures animate without enqueueing; feeding retains a bounded per-actor metadata merge, now with a 50ms leading window and immediate silent statistics. A newer feed suppresses an older same-actor interaction result. The separate 120-second model failure backoff remains. Existing `self_talk_speak_enabled` becomes passive interaction speech (head, click/periodic text, fun feeding); the new default-off `proactive_bubble_speak_enabled` covers delivered ordinary proactive and Todo text bubbles. Both opt-ins reuse one original audio channel/cache/worker/player, with exact receipt, hide epoch, identity, permission, expiry and task guards. Images/statistics/notification-only/errors stay silent. Todo delivery records are unchanged; the optional guarded speech is deferred after the original receipt bookkeeping. See [dual speech report](docs/PR-REPORT-COMPANION-DUAL-SPEECH-2026-10-13.md) and [Windows guide §10](docs/WINDOWS10-COMPANION-ACCEPTANCE.md). Prior Windows Fake concentrated acceptance was reported PASS by the user; this increment and real DeepSeek/Edge/native audio still require separate acceptance.

## Saved AI persona precedence (2026-10-13)

PromptBuilder resolves explicit call override → saved nonblank user prompt differing from factory text → character manifest default → factory fallback. Empty/factory text means no user override, including existing configurations. All chat/proactive/head/feeding requests share this resolver; expression style remains subordinate and privacy/task guards remain intact. Changing the saved persona invalidates old ordinary-chat requests/typewriter output through existing settings refresh, while retaining history. No new editor, preset, schema or companion restructuring. See [persona closeout](docs/PR-REPORT-CHAT-PERSONA-PRIORITY-2026-10-13.md).

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
_Avoid_: Proactive screen recognition, inferred scheduled tasks, automatic speech consent

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
