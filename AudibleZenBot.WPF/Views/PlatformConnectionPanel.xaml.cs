using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using System.Threading.Tasks;
using core.config;



namespace AudibleZenBot.WPF.Views
{
    public partial class PlatformConnectionPanel : UserControl
    {
        private int _tagCounter = 1;
        public string Platform { get; set; } = string.Empty;

        public PlatformConnectionPanel()
        {
            InitializeComponent();
        }

        // Expose commonly used children as public properties for external wiring
        public TextBlock StreamerName => TbStreamerName;
        public Button BtnStreamerLoginControl => BtnStreamerLogin;
        public TextBlock BotName => TbBotName;
        public Button BtnBotLoginControl => BtnBotLogin;
        public CheckBox DisableCheckbox => ChkDisable;
        public TextBox InfoBox => TxtInfo;
        public TextBox TitleBox => TxtTitle;
        public TextBox CategoryBox => TxtCategory;
        public System.Windows.Controls.Primitives.Popup CategoryPopupControl => PopupCategory;
        public ListBox CategorySuggestionsList => CategorySuggestions;
        public TextBox NotificationBox => TxtNotification;
        public Button AddTagButton => BtnAddTag;
        public Button RefreshButton => BtnRefresh;
        public Button SaveButton => BtnSave;
        public WrapPanel TagsWrap => TagsPanel;

        // Add a tag chip to this panel. If tagText is null, generate a placeholder tag.
        public void AddTag(string tagText = null)
        {
            if (string.IsNullOrEmpty(tagText)) tagText = $"tag{_tagCounter++}";

            var border = new Border
            {
                Background = new SolidColorBrush(Color.FromRgb(45, 45, 45)),
                CornerRadius = new CornerRadius(4),
                Padding = new Thickness(6, 4, 6, 4),
                Margin = new Thickness(4)
            };

            var sp = new StackPanel { Orientation = Orientation.Horizontal };
            var tb = new TextBlock { Text = tagText, Foreground = Brushes.White, Margin = new Thickness(0, 0, 6, 0) };
            var btn = new Button { Content = "x", Width = 18, Height = 18, Tag = border };
            btn.Click += (s, e) =>
            {
                if (s is Button b && b.Tag is Border br)
                {
                    TagsPanel.Children.Remove(br);
                }
            };

            sp.Children.Add(tb);
            sp.Children.Add(btn);
            border.Child = sp;
            TagsPanel.Children.Add(border);
        }

        public string GetTagsAsString()
        {
            var tags = new System.Collections.Generic.List<string>();
            foreach (var child in TagsPanel.Children)
            {
                if (child is Border br && br.Child is StackPanel sp && sp.Children.Count > 0)
                {
                    if (sp.Children[0] is TextBlock tb)
                    {
                        var txt = tb.Text?.Trim();
                        if (!string.IsNullOrEmpty(txt)) tags.Add(txt);
                    }
                }
            }
            return string.Join(",", tags);
        }

        // Category suggestion support (used for Twitch Helix suggestions)
        private DispatcherTimer _categoryTimer;
        private string _lastQuery = string.Empty;
        private System.Collections.Generic.List<string> _categoryCache = new System.Collections.Generic.List<string>();

        public void EnableTwitchCategorySuggestions()
        {
            if (_categoryTimer != null) return;
            _categoryTimer = new DispatcherTimer();
            _categoryTimer.Interval = System.TimeSpan.FromMilliseconds(200);
            _categoryTimer.Tick += (s, e) => { _categoryTimer.Stop(); _ = FetchCategorySuggestionsAsync(_lastQuery); };

            CategoryBox.TextChanged += (s, e) => {
                var t = CategoryBox.Text ?? string.Empty;
                _lastQuery = t;
                if (string.IsNullOrWhiteSpace(t)) { PopupCategory.IsOpen = false; _categoryCache.Clear(); return; }
                var q = t.Trim().ToLowerInvariant();
                var matches = _categoryCache.FindAll(x => x.ToLowerInvariant().Contains(q));
                if (matches.Count > 0)
                {
                    CategorySuggestions.ItemsSource = matches.Count > 10 ? matches.GetRange(0,10) : matches;
                    PopupCategory.IsOpen = true;
                }
                _categoryTimer.Stop();
                _categoryTimer.Start();
            };

            CategorySuggestions.MouseDoubleClick += (s, e) => {
                if (CategorySuggestions.SelectedItem is string sel)
                {
                    CategoryBox.Text = sel;
                    PopupCategory.IsOpen = false;
                }
            };
        }

        private async Task FetchCategorySuggestionsAsync(string query)
        {
            try
            {
                var q = (query ?? string.Empty).Trim();
                if (string.IsNullOrEmpty(q)) return;
                var cfg = ConfigModule.GetPlatformConfig("twitch");
                string clientId = "";
                string oauthToken = "";
                if (cfg != null)
                {
                    if (cfg.ContainsKey("client_id")) clientId = cfg["client_id"]?.ToString() ?? "";
                    if (cfg.ContainsKey("oauth_token")) oauthToken = cfg["oauth_token"]?.ToString() ?? "";
                }
                if (string.IsNullOrEmpty(clientId) || string.IsNullOrEmpty(oauthToken))
                {
                    await Dispatcher.InvokeAsync(() => { PopupCategory.IsOpen = false; });
                    return;
                }

                using var http = core.http_client.HttpClientFactory.GetClient(forceNew: true);
                var req = new System.Net.Http.HttpRequestMessage(System.Net.Http.HttpMethod.Get, "https://api.twitch.tv/helix/search/categories?query=" + System.Uri.EscapeDataString(q));
                req.Headers.Add("Client-ID", clientId);
                req.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", oauthToken);
                var resp = await http.SendAsync(req).ConfigureAwait(false);
                var text = await resp.Content.ReadAsStringAsync().ConfigureAwait(false);
                if (!resp.IsSuccessStatusCode)
                {
                    await Dispatcher.InvokeAsync(() => PopupCategory.IsOpen = false);
                    return;
                }
                using var doc = System.Text.Json.JsonDocument.Parse(text);
                var root = doc.RootElement;
                var list = new System.Collections.Generic.List<string>();
                if (root.TryGetProperty("data", out var data) && data.ValueKind == System.Text.Json.JsonValueKind.Array)
                {
                    foreach (var item in data.EnumerateArray())
                    {
                        if (item.TryGetProperty("name", out var name) && name.ValueKind == System.Text.Json.JsonValueKind.String)
                        {
                            list.Add(name.GetString() ?? string.Empty);
                        }
                        if (list.Count >= 12) break;
                    }
                }
                _categoryCache = list;
                var toShow = list.Count > 10 ? list.GetRange(0, 10) : list;
                await Dispatcher.InvokeAsync(() => {
                    CategorySuggestions.ItemsSource = toShow;
                    PopupCategory.IsOpen = CategorySuggestions.Items.Count > 0;
                });
            }
            catch
            {
                await Dispatcher.InvokeAsync(() => PopupCategory.IsOpen = false);
            }
        }
    }
}
