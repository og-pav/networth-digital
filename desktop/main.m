// NetWorth Routine — native macOS wrapper.
//
// The web app is served to a WKWebView through a custom URL scheme rather than
// file:// URLs, because WebKit gives file:// pages an opaque origin and refuses
// them localStorage — which is where the entire routine lives. A custom scheme
// gets a real origin, so storage persists between launches. Nothing is served
// over the network and no port is opened.
//
// Objective-C rather than Swift on purpose: this machine's Command Line Tools
// ship a Swift compiler that disagrees with its own SDK, so `import WebKit`
// fails to build. Clang has no such problem.

#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

static NSString *const kScheme = @"nwroutine";

#pragma mark - Serve the bundled web files

@interface BundleSchemeHandler : NSObject <WKURLSchemeHandler>
@property (nonatomic, strong) NSURL *root;
@end

@implementation BundleSchemeHandler

- (NSString *)mimeForExtension:(NSString *)ext {
    ext = ext.lowercaseString;
    if ([ext isEqualToString:@"html"]) return @"text/html; charset=utf-8";
    if ([ext isEqualToString:@"js"])   return @"text/javascript; charset=utf-8";
    if ([ext isEqualToString:@"css"])  return @"text/css; charset=utf-8";
    if ([ext isEqualToString:@"json"] || [ext isEqualToString:@"webmanifest"])
        return @"application/json; charset=utf-8";
    if ([ext isEqualToString:@"svg"])  return @"image/svg+xml";
    if ([ext isEqualToString:@"png"])  return @"image/png";
    return @"application/octet-stream";
}

- (void)webView:(WKWebView *)webView startURLSchemeTask:(id<WKURLSchemeTask>)task {
    NSString *path = task.request.URL.path;
    if (path.length == 0 || [path isEqualToString:@"/"]) path = @"/index.html";

    NSData *data = nil;

    // The calendar is the one file that must be live rather than bundled — a
    // copy baked in at build time would show yesterday's bookings forever. Read
    // it from the working folder that the sync writes to, and fall back to the
    // bundle so the app still runs if that folder is gone.
    if ([path hasSuffix:@"/calendar.json"] || [path isEqualToString:@"/calendar.json"]) {
        NSString *live = [NSHomeDirectory() stringByAppendingPathComponent:@"daily-routine/calendar.json"];
        data = [NSData dataWithContentsOfFile:live];
    }

    NSURL *file = [[self.root URLByAppendingPathComponent:path] URLByStandardizingPath];
    NSString *rootPath = self.root.URLByStandardizingPath.path;

    // Never serve anything outside the bundle, whatever the page asks for.
    if (!data && [file.path hasPrefix:rootPath]) data = [NSData dataWithContentsOfURL:file];

    if (!data) {
        [task didFailWithError:[NSError errorWithDomain:@"NWRoutine" code:404
            userInfo:@{NSLocalizedDescriptionKey:
                       [NSString stringWithFormat:@"Not found: %@", path]}]];
        return;
    }

    NSHTTPURLResponse *response =
        [[NSHTTPURLResponse alloc] initWithURL:task.request.URL
                                    statusCode:200
                                   HTTPVersion:@"HTTP/1.1"
                                  headerFields:@{@"Content-Type": [self mimeForExtension:file.pathExtension],
                                                 @"Content-Length": @(data.length).stringValue,
                                                 @"Cache-Control": @"no-cache"}];
    [task didReceiveResponse:response];
    [task didReceiveData:data];
    [task didFinish];
}

- (void)webView:(WKWebView *)webView stopURLSchemeTask:(id<WKURLSchemeTask>)task {}
@end

#pragma mark - App

@interface AppDelegate : NSObject <NSApplicationDelegate, WKNavigationDelegate,
                                   WKDownloadDelegate, WKUIDelegate>
@property (nonatomic, strong) NSWindow *window;
@property (nonatomic, strong) WKWebView *webView;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)note {
    NSURL *webRoot = [NSBundle.mainBundle.resourceURL URLByAppendingPathComponent:@"web"];

    BundleSchemeHandler *handler = [BundleSchemeHandler new];
    handler.root = webRoot;

    WKWebViewConfiguration *config = [WKWebViewConfiguration new];
    [config setURLSchemeHandler:handler forURLScheme:kScheme];
    config.websiteDataStore = [WKWebsiteDataStore defaultDataStore];   // persistent localStorage

    self.webView = [[WKWebView alloc] initWithFrame:NSZeroRect configuration:config];
    self.webView.navigationDelegate = self;
    self.webView.UIDelegate = self;
    self.webView.allowsBackForwardNavigationGestures = NO;
    [self.webView setValue:@NO forKey:@"drawsBackground"];

    self.window = [[NSWindow alloc]
        initWithContentRect:NSMakeRect(0, 0, 1080, 820)
                  styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                             NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable |
                             NSWindowStyleMaskFullSizeContentView)
                    backing:NSBackingStoreBuffered
                      defer:NO];
    self.window.title = @"NetWorth Routine";
    self.window.titlebarAppearsTransparent = YES;
    self.window.minSize = NSMakeSize(380, 480);
    self.window.contentView = self.webView;
    [self.window setFrameAutosaveName:@"NetWorthRoutineWindow"];
    [self.window center];
    [self.window makeKeyAndOrderFront:nil];

    [self buildMenu];
    [self.webView loadRequest:[NSURLRequest requestWithURL:
        [NSURL URLWithString:[NSString stringWithFormat:@"%@://app/index.html", kScheme]]]];
    [NSApp activateIgnoringOtherApps:YES];
}

// Clicking the dock icon after closing the window reopens it.
- (BOOL)applicationShouldHandleReopen:(NSApplication *)sender hasVisibleWindows:(BOOL)flag {
    if (!flag) [self.window makeKeyAndOrderFront:nil];
    return YES;
}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender { return YES; }

#pragma mark Backup export
// "Export backup" builds a Blob and clicks a download link, which a plain
// WKWebView silently swallows. Route it to a real save panel instead.

- (void)webView:(WKWebView *)webView
    decidePolicyForNavigationAction:(WKNavigationAction *)action
                    decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {
    if (@available(macOS 11.3, *)) {
        if (action.shouldPerformDownload) { decisionHandler(WKNavigationActionPolicyDownload); return; }
    }
    decisionHandler(WKNavigationActionPolicyAllow);
}

- (void)webView:(WKWebView *)webView
    navigationAction:(WKNavigationAction *)navigationAction
     didBecomeDownload:(WKDownload *)download API_AVAILABLE(macos(11.3)) {
    download.delegate = self;
}

- (void)download:(WKDownload *)download
    decideDestinationUsingResponse:(NSURLResponse *)response
                 suggestedFilename:(NSString *)suggestedFilename
                 completionHandler:(void (^)(NSURL *))completionHandler API_AVAILABLE(macos(11.3)) {
    NSSavePanel *panel = [NSSavePanel savePanel];
    panel.nameFieldStringValue = suggestedFilename;
    panel.directoryURL = [NSFileManager.defaultManager URLsForDirectory:NSDownloadsDirectory
                                                             inDomains:NSUserDomainMask].firstObject;
    [panel beginWithCompletionHandler:^(NSModalResponse result) {
        if (result != NSModalResponseOK || !panel.URL) { completionHandler(nil); return; }
        [NSFileManager.defaultManager removeItemAtURL:panel.URL error:nil];
        completionHandler(panel.URL);
    }];
}

- (void)download:(WKDownload *)download didFailWithError:(NSError *)error
        resumeData:(NSData *)resumeData API_AVAILABLE(macos(11.3)) {
    NSLog(@"download failed: %@", error.localizedDescription);
}

#pragma mark Menus
// Without these there is no Cmd-Q, and no copy/paste in the text fields.

- (void)buildMenu {
    NSMenu *main = [NSMenu new];

    NSMenuItem *appItem = [NSMenuItem new];
    NSMenu *appMenu = [NSMenu new];
    [appMenu addItemWithTitle:@"About NetWorth Routine"
                       action:@selector(orderFrontStandardAboutPanel:) keyEquivalent:@""];
    [appMenu addItem:[NSMenuItem separatorItem]];
    [appMenu addItemWithTitle:@"Hide NetWorth Routine" action:@selector(hide:) keyEquivalent:@"h"];
    [appMenu addItemWithTitle:@"Quit NetWorth Routine" action:@selector(terminate:) keyEquivalent:@"q"];
    appItem.submenu = appMenu;
    [main addItem:appItem];

    NSMenuItem *editItem = [NSMenuItem new];
    NSMenu *edit = [[NSMenu alloc] initWithTitle:@"Edit"];
    [edit addItemWithTitle:@"Undo" action:NSSelectorFromString(@"undo:") keyEquivalent:@"z"];
    [edit addItemWithTitle:@"Redo" action:NSSelectorFromString(@"redo:") keyEquivalent:@"Z"];
    [edit addItem:[NSMenuItem separatorItem]];
    [edit addItemWithTitle:@"Cut" action:@selector(cut:) keyEquivalent:@"x"];
    [edit addItemWithTitle:@"Copy" action:@selector(copy:) keyEquivalent:@"c"];
    [edit addItemWithTitle:@"Paste" action:@selector(paste:) keyEquivalent:@"v"];
    [edit addItemWithTitle:@"Select All" action:@selector(selectAll:) keyEquivalent:@"a"];
    editItem.submenu = edit;
    [main addItem:editItem];

    NSMenuItem *viewItem = [NSMenuItem new];
    NSMenu *view = [[NSMenu alloc] initWithTitle:@"View"];
    [view addItemWithTitle:@"Reload" action:@selector(doReload) keyEquivalent:@"r"];
    [view addItemWithTitle:@"Actual Size" action:@selector(zoomReset) keyEquivalent:@"0"];
    [view addItemWithTitle:@"Zoom In" action:@selector(zoomIn) keyEquivalent:@"+"];
    [view addItemWithTitle:@"Zoom Out" action:@selector(zoomOut) keyEquivalent:@"-"];
    [view addItem:[NSMenuItem separatorItem]];
    [view addItemWithTitle:@"Enter Full Screen" action:@selector(toggleFullScreen:) keyEquivalent:@"f"];
    viewItem.submenu = view;
    [main addItem:viewItem];

    NSMenuItem *winItem = [NSMenuItem new];
    NSMenu *win = [[NSMenu alloc] initWithTitle:@"Window"];
    [win addItemWithTitle:@"Minimise" action:@selector(miniaturize:) keyEquivalent:@"m"];
    [win addItemWithTitle:@"Close" action:@selector(performClose:) keyEquivalent:@"w"];
    winItem.submenu = win;
    [main addItem:winItem];
    NSApp.windowsMenu = win;

    NSApp.mainMenu = main;
}

- (void)doReload  { [self.webView reload]; }
- (void)zoomIn    { self.webView.pageZoom = MIN(self.webView.pageZoom + 0.1, 2.5); }
- (void)zoomOut   { self.webView.pageZoom = MAX(self.webView.pageZoom - 0.1, 0.6); }
- (void)zoomReset { self.webView.pageZoom = 1.0; }

@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication;
        AppDelegate *delegate = [AppDelegate new];
        app.delegate = delegate;
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        [app run];
    }
    return 0;
}
