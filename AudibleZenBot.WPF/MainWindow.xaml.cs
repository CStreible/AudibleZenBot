using System.Windows;
using System.Windows.Controls;

namespace AudibleZenBot.WPF
{
    public partial class MainWindow : Window
    {
        private Views.ChatPage _chatPage = new Views.ChatPage();
        private Views.ConnectionsPage _connectionsPage = new Views.ConnectionsPage();
        private Views.SettingsPage _settingsPage = new Views.SettingsPage();
        private Views.OverlayPage _overlayPage = new Views.OverlayPage();
        private Views.AutomationPage _automationPage = new Views.AutomationPage();

        public MainWindow()
        {
            InitializeComponent();
            NavList.SelectionChanged += NavList_SelectionChanged;
            ContentArea.Content = _chatPage;
        }

        private void NavList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            switch (NavList.SelectedIndex)
            {
                case 0: ContentArea.Content = _chatPage; break;
                case 1: ContentArea.Content = _connectionsPage; break;
                case 2: ContentArea.Content = _settingsPage; break;
                case 3: ContentArea.Content = _overlayPage; break;
                case 4: ContentArea.Content = _automationPage; break;
                default: ContentArea.Content = _chatPage; break;
            }
        }
    }
}
