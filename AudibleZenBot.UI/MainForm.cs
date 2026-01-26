using System;
using System.Linq;
using System.Windows.Forms;

namespace AudibleZenBot.UI {
    public class MainForm : Form {
        // Navigation
        private Panel pnlNav;
        private ListBox lstPages;

        // Content area
        private Panel pnlContent;

        // Platform Connections page controls
        private Panel pnlPlatformConnections;
        private ListBox lstPlatforms;
        private Button btnConnect;
        private Label lblStatus;

        // Placeholders for other pages
        private Panel pnlChatMessages;
        private Panel pnlSettings;
        private Panel pnlOverlayConfig;
        private Panel pnlAutomation;

        public MainForm() {
            this.Text = "AudibleZenBot";
            this.Width = 900;
            this.Height = 600;

            // Left navigation panel
            pnlNav = new Panel() { Left = 0, Top = 0, Width = 180, Height = this.ClientSize.Height, Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left };
            lstPages = new ListBox() { Left = 10, Top = 10, Width = 160, Height = pnlNav.Height - 20, Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left };
            lstPages.Items.AddRange(new object[] { "Chat Messages", "Platform Connections", "Settings", "Chat Overlay Configuration", "Automation" });
            lstPages.SelectedIndexChanged += LstPages_SelectedIndexChanged;
            pnlNav.Controls.Add(lstPages);

            // Content panel
            pnlContent = new Panel() { Left = pnlNav.Right + 10, Top = 0, Width = this.ClientSize.Width - pnlNav.Width - 20, Height = this.ClientSize.Height, Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right };

            // Platform Connections page
            pnlPlatformConnections = new Panel() { Dock = DockStyle.Fill, Visible = false };
            lstPlatforms = new ListBox() { Left = 10, Top = 10, Width = 240, Height = 300 }; 
            lstPlatforms.Items.Add("Twitch");
            lstPlatforms.Items.Add("YouTube");
            lstPlatforms.Items.Add("Trovo");
            lstPlatforms.Items.Add("Kick");

            btnConnect = new Button() { Left = 260, Top = 10, Width = 100, Text = "Connect" };
            btnConnect.Click += BtnConnect_Click;

            lblStatus = new Label() { Left = 260, Top = 50, Width = 400, Height = 24, Text = "Status: idle" };

            pnlPlatformConnections.Controls.Add(lstPlatforms);
            pnlPlatformConnections.Controls.Add(btnConnect);
            pnlPlatformConnections.Controls.Add(lblStatus);

            // Other pages (simple placeholders for now)
            pnlChatMessages = new Panel() { Dock = DockStyle.Fill, Visible = false };
            pnlChatMessages.Controls.Add(new Label() { Text = "Chat Messages", Left = 10, Top = 10 });

            pnlSettings = new Panel() { Dock = DockStyle.Fill, Visible = false };
            pnlSettings.Controls.Add(new Label() { Text = "Settings", Left = 10, Top = 10 });

            pnlOverlayConfig = new Panel() { Dock = DockStyle.Fill, Visible = false };
            pnlOverlayConfig.Controls.Add(new Label() { Text = "Chat Overlay Configuration", Left = 10, Top = 10 });

            pnlAutomation = new Panel() { Dock = DockStyle.Fill, Visible = false };
            // Automation tabset
            var tab = new TabControl() { Dock = DockStyle.Fill };
            var tabVariables = new TabPage("Variables");
            var tabFunctions = new TabPage("Functions");
            var tabTriggers = new TabPage("Triggers");
            var tabTimers = new TabPage("Timers");
            var tabEvents = new TabPage("Events");

            // Variables tab: scrollable panel with add/delete buttons
            var varsPanel = new Panel() { Dock = DockStyle.Fill, AutoScroll = true };
            var varsToolbar = new Panel() { Dock = DockStyle.Top, Height = 40 };
            var addVarBtn = new Button() { Text = "Add Variable", Left = 10, Top = 6, Width = 120 };
            var delVarBtn = new Button() { Text = "Delete Selected", Left = 140, Top = 6, Width = 120 };
            varsToolbar.Controls.Add(addVarBtn);
            varsToolbar.Controls.Add(delVarBtn);
            tabVariables.Controls.Add(varsPanel);
            tabVariables.Controls.Add(varsToolbar);

            // container for VariableRow controls
            var varsContainer = new Panel() { Dock = DockStyle.Top, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink };
            varsPanel.Controls.Add(varsContainer);

            addVarBtn.Click += (s, e) => {
                var row = new AudibleZenBot.UI.Controls.VariableRow();
                // place at top
                row.Dock = DockStyle.Top;
                varsContainer.Controls.Add(row);
                // ensure newest appears first visually
                varsContainer.Controls.SetChildIndex(row, 0);
            };

            delVarBtn.Click += (s, e) => {
                // remove selected items (based on NameBox.SelectionLength > 0 as quick heuristic)
                var toRemove = varsContainer.Controls.OfType<AudibleZenBot.UI.Controls.VariableRow>().Where(r => r.NameBox.Focused).ToList();
                foreach (var r in toRemove) varsContainer.Controls.Remove(r);
            };

            // Functions tab: simple editor placeholder
            var functionsEditor = new TextBox() { Multiline = true, Dock = DockStyle.Fill, Font = new System.Drawing.Font("Consolas", 10f), ScrollBars = ScrollBars.Both }; 
            tabFunctions.Controls.Add(functionsEditor);

            tab.Controls.Add(tabVariables);
            tab.Controls.Add(tabFunctions);
            tab.Controls.Add(tabTriggers);
            tab.Controls.Add(tabTimers);
            tab.Controls.Add(tabEvents);

            pnlAutomation.Controls.Add(tab);

            pnlContent.Controls.Add(pnlPlatformConnections);
            pnlContent.Controls.Add(pnlChatMessages);
            pnlContent.Controls.Add(pnlSettings);
            pnlContent.Controls.Add(pnlOverlayConfig);
            pnlContent.Controls.Add(pnlAutomation);

            // Add to form
            this.Controls.Add(pnlNav);
            this.Controls.Add(pnlContent);

            // Select first page by default
            lstPages.SelectedIndex = 0;
        }

        private void LstPages_SelectedIndexChanged(object? sender, EventArgs e) {
            var sel = lstPages.SelectedItem?.ToString() ?? string.Empty;
            pnlPlatformConnections.Visible = sel == "Platform Connections";
            pnlChatMessages.Visible = sel == "Chat Messages";
            pnlSettings.Visible = sel == "Settings";
            pnlOverlayConfig.Visible = sel == "Chat Overlay Configuration";
            pnlAutomation.Visible = sel == "Automation";
        }

        private void BtnConnect_Click(object? sender, EventArgs e) {
            if (lstPlatforms.SelectedItem == null) {
                MessageBox.Show("Select a platform first.", "Info", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            var platformName = lstPlatforms.SelectedItem.ToString() ?? string.Empty;
            lblStatus.Text = $"Status: connecting to {platformName}...";

            try {
                // Map display name -> internal platform id where available
                string platformId = platformName.ToLower() switch {
                    "twitch" => core.platforms.PlatformIds.Twitch,
                    "youtube" => core.platforms.PlatformIds.YouTube,
                    "trovo" => core.platforms.PlatformIds.Trovo,
                    "kick" => core.platforms.PlatformIds.Kick,
                    _ => platformName
                };

                // Call the connector's ConnectToPlatform (blocks briefly)
                platform_connectors.twitch_connector.Twitch_connectorModule.ConnectToPlatform(platformId).GetAwaiter().GetResult();
                lblStatus.Text = $"Status: connected to {platformName}";
            } catch (Exception ex) {
                lblStatus.Text = $"Status: error: {ex.Message}";
            }
        }
    }
}
