using System;
using System.Threading.Tasks;

namespace core.twitch_emotes {
    public static class Twitch_emotesModule {
        // Original: def __init__(self)
        public static void Init() {
            // TODO: implement
        }

        // Original: def start(self)
        public static void Start() {
            // TODO: implement
        }

        // Original: def pyqtSlot(*args, **kwargs)
        public static void PyqtSlot() {
            // TODO: implement
        }

        // Original: def _d(f)
        public static void D(object? f) {
            // TODO: implement
        }

        // Original: def __init__(self, code: str, message: str = '')
        public static void Init(string? code, string? message = null) {
            // TODO: implement
        }

        // Original: def __init__(self, config=None)
        public static void Init(object? config = null) {
            // TODO: implement
        }

        // Original: def _headers(self)
        public static void Headers() {
            // TODO: implement
        }

        // Original: def _request_with_backoff(self, url: str, params=None, timeout: int = 10, max_retries: int = 3)
        public static void RequestWithBackoff(string? url, object? @params = null, int? timeout = null, int? max_retries = null) {
            // TODO: implement
        }

        // Original: def fetch_global_emotes(self)
        public static void FetchGlobalEmotes() {
            // TODO: implement
        }

        // Original: def fetch_emote_sets(self, emote_set_ids)
        public static void FetchEmoteSets(object? emote_set_ids) {
            // TODO: implement
        }

        // Original: def start_emote_set_throttler(self)
        public static void StartEmoteSetThrottler() {
            // TODO: implement
        }

        // Original: def _worker()
        public static void Worker() {
            // TODO: implement
        }

        // Original: def stop_emote_set_throttler(self, timeout: float = 1.0)
        public static void StopEmoteSetThrottler(double? timeout = null) {
            // TODO: implement
        }

        // Original: def schedule_emote_set_fetch(self, emote_set_ids)
        public static void ScheduleEmoteSetFetch(object? emote_set_ids) {
            // TODO: implement
        }

        // Original: def fetch_channel_emotes(self, broadcaster_id: str)
        public static void FetchChannelEmotes(string? broadcaster_id) {
            // Prefer canonical streamer id when broadcaster_id not provided
            try {
                if (string.IsNullOrEmpty(broadcaster_id)) {
                    broadcaster_id = core.config.ConfigModule.GetPlatformUserId(core.platforms.PlatformIds.Twitch, "streamer", "");
                }
            } catch { }
            // TODO: implement remaining logic
        }

        // Original: def dump_channel_emotes(self, broadcaster_id: str)
        public static void DumpChannelEmotes(string? broadcaster_id) {
            // TODO: implement
        }

        // Original: def _select_image_url(self, emobj: dict)
        public static void SelectImageUrl(System.Collections.Generic.Dictionary<string,object>? emobj) {
            // TODO: implement
        }

        // Original: def _prefetch_emote_images(self, emote_ids)
        public static void PrefetchEmoteImages(object? emote_ids) {
            // TODO: implement
        }

        // Original: def get_emote_data_uri(self, emote_id, broadcaster_id=None)
        public static void GetEmoteDataUri(object? emote_id, object? broadcaster_id = null) {
            try {
                if (broadcaster_id == null || string.IsNullOrEmpty(broadcaster_id.ToString())) {
                    var bid = core.config.ConfigModule.GetPlatformUserId(core.platforms.PlatformIds.Twitch, "streamer", "");
                    broadcaster_id = string.IsNullOrEmpty(bid) ? broadcaster_id : (object)bid;
                }
            } catch { }
            // TODO: implement remaining logic
        }

        // Original: def prefetch_global(self, background: bool = True)
        public static void PrefetchGlobal(bool? background = null) {
            // TODO: implement
        }

        // Original: def _work()
        public static void Work() {
            // TODO: implement
        }

        // Original: def prefetch_channel(self, broadcaster_id: str, background: bool = True)
        public static void PrefetchChannel(string? broadcaster_id, bool? background = null) {
            try {
                if (string.IsNullOrEmpty(broadcaster_id)) {
                    broadcaster_id = core.config.ConfigModule.GetPlatformUserId(core.platforms.PlatformIds.Twitch, "streamer", "");
                }
            } catch { }
            // TODO: implement remaining logic
        }

        // Original: def shutdown(self, timeout: float = 1.0)
        public static void Shutdown(double? timeout = null) {
            // TODO: implement
        }

        // Original: def get_manager(config: Optional[object] = None)
        public static void GetManager(object? config = null) {
            // TODO: implement
        }

    }

    public class QObject {

        public QObject() {
        }

    }

    public class QThread {
        public object? started { get; set; }
        public object? finished { get; set; }


        // Original: def __init__(self)
        public QThread() {
            // TODO: implement constructor
            this.started = null;
            this.finished = null;
        }

        // Original: def start(self)
        public void Start() {
            // TODO: implement
        }

        // Original: def pyqtSlot(*args, **kwargs)
        public void PyqtSlot() {
            // TODO: implement
        }

        // Original: def _d(f)
        public void D(object? f) {
            // TODO: implement
        }

    }

    public class PrefetchError {
        public object? code { get; set; }
        public object? message { get; set; }


        // Original: def __init__(self, code: str, message: str = '')
        public PrefetchError(string? code, string? message = null) {
            // TODO: implement constructor
            this.code = null;
            this.message = null;
        }

    }

    public class TwitchEmoteManager {
        public bool? config { get; set; }
        public object? session { get; set; }
        public double? _backoff_base { get; set; }
        public int? _max_retries { get; set; }
        public object? _emote_set_queue { get; set; }
        public bool? _throttler_thread { get; set; }
        public object? _throttler_stop { get; set; }
        public object? _batch_interval { get; set; }
        public int? _emote_set_batch_size { get; set; }
        public object? id_map { get; set; }
        public object? name_map { get; set; }
        public bool? _warmed_global { get; set; }
        public object? _warmed_channels { get; set; }
        public System.Collections.Generic.List<object>? _prefetch_threads { get; set; }
        public object? cache_dir { get; set; }
        public object? _header { get; set; }
        public object? _last_request_attempts { get; set; }
        public object? _request_with_backof { get; set; }
        public object? _prefetch_emote_image { get; set; }
        public object? fetch_emote_set { get; set; }
        public object? start_emote_set_throttle { get; set; }
        public int? _last_emote_set_count { get; set; }
        public object? schedule_emote_set_fetc { get; set; }
        public object? fetch_channel_emote { get; set; }
        public object? _select_image_ur { get; set; }
        public object? fetch_global_emote { get; set; }
        public bool? _shutting_down { get; set; }


        // Original: def __init__(self, config=None)
        public TwitchEmoteManager(object? config = null) {
            // TODO: implement constructor
            this.config = null;
            this.session = null;
            this._backoff_base = null;
            this._max_retries = null;
            this._emote_set_queue = null;
            this._throttler_thread = null;
            this._throttler_stop = null;
            this._batch_interval = null;
            this._emote_set_batch_size = null;
            this.id_map = null;
            this.name_map = null;
            this._warmed_global = null;
            this._warmed_channels = null;
            this._prefetch_threads = null;
            this.cache_dir = null;
            this._header = null;
            this._last_request_attempts = null;
            this._request_with_backof = null;
            this._prefetch_emote_image = null;
            this.fetch_emote_set = null;
            this.start_emote_set_throttle = null;
            this._last_emote_set_count = null;
            this.schedule_emote_set_fetc = null;
            this.fetch_channel_emote = null;
            this._select_image_ur = null;
            this.fetch_global_emote = null;
            this._shutting_down = null;
        }

        // Original: def _headers(self)
        public void Headers() {
            // TODO: implement
        }

        // Original: def _request_with_backoff(self, url: str, params=None, timeout: int = 10, max_retries: int = 3)
        public void RequestWithBackoff(string? url, object? @params = null, int? timeout = null, int? max_retries = null) {
            // TODO: implement
        }

        // Original: def fetch_global_emotes(self)
        public void FetchGlobalEmotes() {
            // TODO: implement
        }

        // Original: def fetch_emote_sets(self, emote_set_ids)
        public void FetchEmoteSets(object? emote_set_ids) {
            // TODO: implement
        }

        // Original: def start_emote_set_throttler(self)
        public void StartEmoteSetThrottler() {
            // TODO: implement
        }

        // Original: def _worker()
        public void Worker() {
            // TODO: implement
        }

        // Original: def stop_emote_set_throttler(self, timeout: float = 1.0)
        public void StopEmoteSetThrottler(double? timeout = null) {
            // TODO: implement
        }

        // Original: def schedule_emote_set_fetch(self, emote_set_ids)
        public void ScheduleEmoteSetFetch(object? emote_set_ids) {
            // TODO: implement
        }

        // Original: def fetch_channel_emotes(self, broadcaster_id: str)
        public void FetchChannelEmotes(string? broadcaster_id) {
            // TODO: implement
        }

        // Original: def dump_channel_emotes(self, broadcaster_id: str)
        public void DumpChannelEmotes(string? broadcaster_id) {
            // TODO: implement
        }

        // Original: def _select_image_url(self, emobj: dict)
        public void SelectImageUrl(System.Collections.Generic.Dictionary<string,object>? emobj) {
            // TODO: implement
        }

        // Original: def _prefetch_emote_images(self, emote_ids)
        public void PrefetchEmoteImages(object? emote_ids) {
            // TODO: implement
        }

        // Original: def get_emote_data_uri(self, emote_id, broadcaster_id=None)
        public void GetEmoteDataUri(object? emote_id, object? broadcaster_id = null) {
            // TODO: implement
        }

        // Original: def prefetch_global(self, background: bool = True)
        public void PrefetchGlobal(bool? background = null) {
            // TODO: implement
        }

        // Original: def _work()
        public void Work() {
            // TODO: implement
        }

        // Original: def prefetch_channel(self, broadcaster_id: str, background: bool = True)
        public void PrefetchChannel(string? broadcaster_id, bool? background = null) {
            // TODO: implement
        }

        // Original: def shutdown(self, timeout: float = 1.0)
        public void Shutdown(double? timeout = null) {
            // TODO: implement
        }

        // Original: def get_manager(config: Optional[object] = None)
        public void GetManager(object? config = null) {
            // TODO: implement
        }

    }

}

