using System;
using System.Threading.Tasks;

namespace ui.overlay_page {
    public static class Overlay_pageModule {
        // Original: def get_windows_camera_names()
        public static void GetWindowsCameraNames() {
            // TODO: implement
        }

        // Original: def enumerate_video_devices()
        public static void EnumerateVideoDevices() {
            // TODO: implement
        }

        // Original: def __init__(self, overlay_server, config=None, parent=None)
        public static void Init(object? overlay_server, object? config = null, object? parent = null) {
            // TODO: implement
        }

        // Original: def initUI(self)
        public static void InitUI() {
            // TODO: implement
        }

        // Original: def createGroupBox(self, title)
        public static void CreateGroupBox(object? title) {
            // TODO: implement
        }

        // Original: def createLabel(self, text, bold=False, margin_top=False, margin_left=False)
        public static void CreateLabel(object? text, bool? bold = null, bool? margin_top = null, bool? margin_left = null) {
            // TODO: implement
        }

        // Original: def createComboBox(self, items)
        public static void CreateComboBox(object? items) {
            // TODO: implement
        }

        // Original: def createSpinBox(self, min_val, max_val, default_val, suffix="")
        public static void CreateSpinBox(object? min_val, object? max_val, object? default_val, string? suffix = null) {
            // TODO: implement
        }

        // Original: def createFontComboBox(self)
        public static void CreateFontComboBox() {
            // TODO: implement
        }

        // Original: def createSlider(self, min_val, max_val, default_val)
        public static void CreateSlider(object? min_val, object? max_val, object? default_val) {
            // TODO: implement
        }

        // Original: def getButtonStyle(self, bg_color, hover_color)
        public static void GetButtonStyle(object? bg_color, object? hover_color) {
            // TODO: implement
        }

        // Original: def getColorButtonStyle(self, bg_color)
        public static void GetColorButtonStyle(object? bg_color) {
            // TODO: implement
        }

        // Original: def onOverlayServerStarted(self, url)
        public static void OnOverlayServerStarted(object? url) {
            // TODO: implement
        }

        // Original: def onRefreshDevices(self)
        public static void OnRefreshDevices() {
            // TODO: implement
        }

        // Original: def onDevicesUpdated(self, devices)
        public static void OnDevicesUpdated(object? devices) {
            // TODO: implement
        }

        // Original: def copyUrl(self)
        public static void CopyUrl() {
            // TODO: implement
        }

        // Original: def resetCopyButton(self, original_text)
        public static void ResetCopyButton(object? original_text) {
            // TODO: implement
        }

        // Original: def openInBrowser(self)
        public static void OpenInBrowser() {
            // TODO: implement
        }

        // Original: def chooseMsgBgColor(self)
        public static void ChooseMsgBgColor() {
            // TODO: implement
        }

        // Original: def chooseOverlayBgColor(self)
        public static void ChooseOverlayBgColor() {
            // TODO: implement
        }

        // Original: def onOverlayBgTypeChanged(self, bg_type)
        public static void OnOverlayBgTypeChanged(object? bg_type) {
            // TODO: implement
        }

        // Original: def browseOverlayMedia(self)
        public static void BrowseOverlayMedia() {
            // TODO: implement
        }

        // Original: def getSettings(self)
        public static void GetSettings() {
            // TODO: implement
        }

        // Original: def loadSettings(self)
        public static void LoadSettings() {
            // TODO: implement
        }

        // Original: def saveSettings(self)
        public static void SaveSettings() {
            // TODO: implement
        }

        // Original: def onSettingsChanged(self)
        public static void OnSettingsChanged() {
            // TODO: implement
        }

    }

    public class OverlayPage {
        public object? overlay_server { get; set; }
        public object? config { get; set; }
        public bool? overlay_url { get; set; }
        public object? initU { get; set; }
        public object? createGroupBo { get; set; }
        public object? url_label { get; set; }
        public object? copy_btn { get; set; }
        public object? getButtonStyl { get; set; }
        public object? open_btn { get; set; }
        public object? createLabe { get; set; }
        public object? username_font_combo { get; set; }
        public object? createFontComboBo { get; set; }
        public object? username_font_size_spin { get; set; }
        public object? createSpinBo { get; set; }
        public object? show_badges_check { get; set; }
        public object? show_platform_check { get; set; }
        public object? message_font_combo { get; set; }
        public object? message_font_size_spin { get; set; }
        public object? direction_combo { get; set; }
        public object? createComboBo { get; set; }
        public object? duration_spin { get; set; }
        public object? entry_combo { get; set; }
        public object? exit_combo { get; set; }
        public object? max_messages_spin { get; set; }
        public object? msg_bg_color_btn { get; set; }
        public object? getColorButtonStyl { get; set; }
        public object? msg_bg_color { get; set; }
        public object? msg_opacity_slider { get; set; }
        public object? createSlide { get; set; }
        public object? msg_opacity_value { get; set; }
        public object? msg_blur_spin { get; set; }
        public bool? overlay_bg_combo { get; set; }
        public object? overlay_bg_color_btn { get; set; }
        public object? overlay_bg_color { get; set; }
        public object? overlay_media_browse_btn { get; set; }
        public object? overlay_media_path { get; set; }
        public bool? overlay_image_path { get; set; }
        public bool? overlay_video_path { get; set; }
        public object? overlay_device_combo { get; set; }
        public object? refresh_devices_btn { get; set; }
        public object? setLayou { get; set; }
        public object? loadSetting { get; set; }
        public object? resetCopyButto { get; set; }
        public object? onSettingsChange { get; set; }
        public object? getSetting { get; set; }
        public object? saveSetting { get; set; }


        // Original: def __init__(self, overlay_server, config=None, parent=None)
        public OverlayPage(object? overlay_server, object? config = null, object? parent = null) {
            // TODO: implement constructor
            this.overlay_server = null;
            this.config = null;
            this.overlay_url = null;
            this.initU = null;
            this.createGroupBo = null;
            this.url_label = null;
            this.copy_btn = null;
            this.getButtonStyl = null;
            this.open_btn = null;
            this.createLabe = null;
            this.username_font_combo = null;
            this.createFontComboBo = null;
            this.username_font_size_spin = null;
            this.createSpinBo = null;
            this.show_badges_check = null;
            this.show_platform_check = null;
            this.message_font_combo = null;
            this.message_font_size_spin = null;
            this.direction_combo = null;
            this.createComboBo = null;
            this.duration_spin = null;
            this.entry_combo = null;
            this.exit_combo = null;
            this.max_messages_spin = null;
            this.msg_bg_color_btn = null;
            this.getColorButtonStyl = null;
            this.msg_bg_color = null;
            this.msg_opacity_slider = null;
            this.createSlide = null;
            this.msg_opacity_value = null;
            this.msg_blur_spin = null;
            this.overlay_bg_combo = null;
            this.overlay_bg_color_btn = null;
            this.overlay_bg_color = null;
            this.overlay_media_browse_btn = null;
            this.overlay_media_path = null;
            this.overlay_image_path = null;
            this.overlay_video_path = null;
            this.overlay_device_combo = null;
            this.refresh_devices_btn = null;
            this.setLayou = null;
            this.loadSetting = null;
            this.resetCopyButto = null;
            this.onSettingsChange = null;
            this.getSetting = null;
            this.saveSetting = null;
        }

        // Original: def initUI(self)
        public void InitUI() {
            // TODO: implement
        }

        // Original: def createGroupBox(self, title)
        public void CreateGroupBox(object? title) {
            // TODO: implement
        }

        // Original: def createLabel(self, text, bold=False, margin_top=False, margin_left=False)
        public void CreateLabel(object? text, bool? bold = null, bool? margin_top = null, bool? margin_left = null) {
            // TODO: implement
        }

        // Original: def createComboBox(self, items)
        public void CreateComboBox(object? items) {
            // TODO: implement
        }

        // Original: def createSpinBox(self, min_val, max_val, default_val, suffix="")
        public void CreateSpinBox(object? min_val, object? max_val, object? default_val, string? suffix = null) {
            // TODO: implement
        }

        // Original: def createFontComboBox(self)
        public void CreateFontComboBox() {
            // TODO: implement
        }

        // Original: def createSlider(self, min_val, max_val, default_val)
        public void CreateSlider(object? min_val, object? max_val, object? default_val) {
            // TODO: implement
        }

        // Original: def getButtonStyle(self, bg_color, hover_color)
        public void GetButtonStyle(object? bg_color, object? hover_color) {
            // TODO: implement
        }

        // Original: def getColorButtonStyle(self, bg_color)
        public void GetColorButtonStyle(object? bg_color) {
            // TODO: implement
        }

        // Original: def onOverlayServerStarted(self, url)
        public void OnOverlayServerStarted(object? url) {
            // TODO: implement
        }

        // Original: def onRefreshDevices(self)
        public void OnRefreshDevices() {
            // TODO: implement
        }

        // Original: def onDevicesUpdated(self, devices)
        public void OnDevicesUpdated(object? devices) {
            // TODO: implement
        }

        // Original: def copyUrl(self)
        public void CopyUrl() {
            // TODO: implement
        }

        // Original: def resetCopyButton(self, original_text)
        public void ResetCopyButton(object? original_text) {
            // TODO: implement
        }

        // Original: def openInBrowser(self)
        public void OpenInBrowser() {
            // TODO: implement
        }

        // Original: def chooseMsgBgColor(self)
        public void ChooseMsgBgColor() {
            // TODO: implement
        }

        // Original: def chooseOverlayBgColor(self)
        public void ChooseOverlayBgColor() {
            // TODO: implement
        }

        // Original: def onOverlayBgTypeChanged(self, bg_type)
        public void OnOverlayBgTypeChanged(object? bg_type) {
            // TODO: implement
        }

        // Original: def browseOverlayMedia(self)
        public void BrowseOverlayMedia() {
            // TODO: implement
        }

        // Original: def getSettings(self)
        public void GetSettings() {
            // TODO: implement
        }

        // Original: def loadSettings(self)
        public void LoadSettings() {
            // TODO: implement
        }

        // Original: def saveSettings(self)
        public void SaveSettings() {
            // TODO: implement
        }

        // Original: def onSettingsChanged(self)
        public void OnSettingsChanged() {
            // TODO: implement
        }

    }

}

