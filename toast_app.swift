import AppKit

class ToastWindow: NSWindow {
    let messageLabel: NSTextField
    let countdownLabel: NSTextField
    var countdownTimer: Timer?
    var remainingSeconds: Int = 0
    var fadeDuration: TimeInterval = 0.5

    init(title: String, message: String, duration: TimeInterval, countdown: Int) {
        let width: CGFloat = 340
        let padding: CGFloat = 16

        // Create message label to measure height
        messageLabel = NSTextField(labelWithString: message)
        messageLabel.font = NSFont.systemFont(ofSize: 13)
        messageLabel.textColor = NSColor.white
        messageLabel.maximumNumberOfLines = 0
        messageLabel.preferredMaxLayoutWidth = width - padding * 2

        // Title label
        let titleLabel = NSTextField(labelWithString: title)
        titleLabel.font = NSFont.boldSystemFont(ofSize: 14)
        titleLabel.textColor = NSColor.white

        // Countdown label
        countdownLabel = NSTextField(labelWithString: "")
        countdownLabel.font = NSFont.monospacedDigitSystemFont(ofSize: 12, weight: .medium)
        countdownLabel.textColor = NSColor(white: 1.0, alpha: 0.7)
        countdownLabel.isHidden = countdown <= 0

        // Calculate layout
        let titleHeight: CGFloat = 20
        let messageSize = messageLabel.sizeThatFits(NSSize(width: width - padding * 2, height: .greatestFiniteMagnitude))
        let countdownHeight: CGFloat = countdown > 0 ? 22 : 0
        let spacing: CGFloat = 4
        let totalHeight = padding + titleHeight + spacing + messageSize.height + (countdown > 0 ? spacing + countdownHeight : 0) + padding

        // Position at top-right of main screen
        let screen = NSScreen.main!
        let x = screen.visibleFrame.maxX - width - 16
        let y = screen.visibleFrame.maxY - totalHeight - 16
        let frame = NSRect(x: x, y: y, width: width, height: totalHeight)

        super.init(contentRect: frame, styleMask: .borderless, backing: .buffered, defer: false)

        self.isOpaque = false
        self.backgroundColor = .clear
        self.level = .floating
        self.collectionBehavior = [.canJoinAllSpaces, .stationary]
        self.hasShadow = true

        // Background view with rounded corners (fully opaque)
        let bg = NSView(frame: NSRect(x: 0, y: 0, width: width, height: totalHeight))
        bg.wantsLayer = true
        bg.layer?.backgroundColor = NSColor(white: 0.15, alpha: 1.0).cgColor
        bg.layer?.cornerRadius = 12
        bg.layer?.masksToBounds = true
        contentView = bg

        // Layout from top
        var yPos = totalHeight - padding - titleHeight
        titleLabel.frame = NSRect(x: padding, y: yPos, width: width - padding * 2, height: titleHeight)
        bg.addSubview(titleLabel)

        yPos -= spacing + messageSize.height
        messageLabel.frame = NSRect(x: padding, y: yPos, width: width - padding * 2, height: messageSize.height)
        bg.addSubview(messageLabel)

        if countdown > 0 {
            yPos -= spacing + countdownHeight
            countdownLabel.frame = NSRect(x: padding, y: yPos, width: width - padding * 2, height: countdownHeight)
            bg.addSubview(countdownLabel)

            remainingSeconds = countdown
            updateCountdownText()
            countdownTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
                guard let self = self else { return }
                self.remainingSeconds -= 1
                if self.remainingSeconds <= 0 {
                    self.countdownTimer?.invalidate()
                    self.countdownLabel.stringValue = "almost done..."
                } else {
                    self.updateCountdownText()
                }
            }
        }

        // Show and schedule fade-out
        self.alphaValue = 0
        self.orderFrontRegardless()

        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.3
            self.animator().alphaValue = 1
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + duration) {
            self.fadeOutAndClose()
        }

        // Handle SIGTERM: fade out gracefully when parent process kills us
        let termSource = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
        termSource.setEventHandler { [weak self] in
            self?.fadeOutAndClose()
        }
        termSource.resume()
        signal(SIGTERM, SIG_IGN) // Let DispatchSource handle it
    }

    override func mouseDown(with event: NSEvent) {
        fadeOutAndClose()
    }

    func updateCountdownText() {
        let mins = remainingSeconds / 60
        let secs = remainingSeconds % 60
        if mins > 0 {
            countdownLabel.stringValue = "⏱ ~\(mins)m \(secs)s remaining"
        } else {
            countdownLabel.stringValue = "⏱ ~\(secs)s remaining"
        }
    }

    func fadeOutAndClose() {
        countdownTimer?.invalidate()
        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = fadeDuration
            self.animator().alphaValue = 0
        }, completionHandler: {
            self.close()
            NSApp.terminate(nil)
        })
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: ToastWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let args = CommandLine.arguments
        guard args.count >= 3 else {
            print("Usage: notify <title> <message> [duration] [countdown_seconds]")
            NSApp.terminate(nil)
            return
        }
        let title = args[1]
        let message = args[2]
        let duration = args.count >= 4 ? (Double(args[3]) ?? 3) : 3.0
        let countdown = args.count >= 5 ? (Int(args[4]) ?? 0) : 0

        window = ToastWindow(title: title, message: message, duration: duration, countdown: countdown)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
