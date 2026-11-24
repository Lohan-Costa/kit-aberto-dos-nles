// Sonda NATIVA de arrasto (macOS): o que um programa oferece de verdade quando se arrasta algo dele.
// A irmã da `arrasto_nativo.py` (Windows, IDropTarget). Compile FORA do SSD e rode:
//
//     swiftc -O "$PWD/arrasto_nativo_mac.swift" -o <scratchpad>/sonda_arrasto   (caminho COMPLETO: a pasta de saída sai dele)
//     <scratchpad>/sonda_arrasto <rotulo> [x y]        # abre uma janela "SONDA ARRASTO <rotulo>": arraste para ela
//
// Duas escutas, porque no Mac a janela só recebe os tipos que registrou e um programa pode oferecer tipos privados:
// (1) a janela (tipos conhecidos + os do sistema) e (2) a área de transferência de ARRASTO do sistema
// (NSPasteboard .drag), lida a cada 0,1 s — vê TUDO o que a origem pôs, mesmo que a janela não aceite.
// A sonda NUNCA aceita o soltar (performDragOperation = false): o arrasto volta, a origem não faz nada.
// Relatório e conteúdos em `piloto/saida/sondas/arrasto/<rotulo>/` (fora do Git).
import AppKit

let LIMITE = 4 * 1024 * 1024
let args = CommandLine.arguments
let rotulo = args.count > 1 ? args[1] : "sonda"
let aqui = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
let pasta = aqui.deletingLastPathComponent().appendingPathComponent("saida/sondas/arrasto/\(rotulo)")
try? FileManager.default.createDirectory(at: pasta, withIntermediateDirectories: true)
let relatorio = pasta.appendingPathComponent("relatorio.txt")

func escrever(_ s: String) {
    let linha = s + "\n"
    print(s); fflush(stdout)
    if let h = try? FileHandle(forWritingTo: relatorio) { h.seekToEndOfFile(); h.write(linha.data(using: .utf8)!); h.closeFile() }
    else { try? linha.write(to: relatorio, atomically: true, encoding: .utf8) }
}

func legivel(_ d: Data) -> String {
    let pedaco = d.prefix(600)
    if let s = String(data: pedaco, encoding: .utf8), s.unicodeScalars.filter({ $0.value < 32 && $0 != "\n" && $0 != "\t" && $0 != "\r" }).count < 4 {
        return "utf8: " + s.replacingOccurrences(of: "\n", with: "⏎")
    }
    if pedaco.count >= 4, pedaco[pedaco.startIndex + 1] == 0, let s = String(data: pedaco, encoding: .utf16LittleEndian) {
        return "utf16: " + s.replacingOccurrences(of: "\n", with: "⏎")
    }
    return "hex: " + pedaco.prefix(64).map { String(format: "%02x", $0) }.joined(separator: " ")
}

var rodada = 0
func despejar(_ pb: NSPasteboard, _ onde: String) {
    rodada += 1
    let hora = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
    escrever("── \(hora) · \(onde) · rodada \(rodada) · changeCount \(pb.changeCount) · itens \(pb.pasteboardItems?.count ?? 0)")
    for (i, item) in (pb.pasteboardItems ?? []).enumerated() {
        for t in item.types {
            guard let d = item.data(forType: t) else { escrever("  [\(i)] \(t.rawValue) — sem dado (promessa?)"); continue }
            let nome = "r\(rodada)_i\(i)_" + t.rawValue.replacingOccurrences(of: "/", with: "_") + ".bin"
            if d.count <= LIMITE { try? d.write(to: pasta.appendingPathComponent(nome)) }
            escrever("  [\(i)] \(t.rawValue) · \(d.count) B · \(legivel(d))")
        }
    }
}

final class Alvo: NSView {
    override func draggingEntered(_ s: NSDraggingInfo) -> NSDragOperation {
        despejar(s.draggingPasteboard, "janela: entrou (origem \(s.draggingSource.map { "\(type(of: $0))" } ?? "outro processo"), máscara \(s.draggingSourceOperationMask.rawValue))")
        return .copy
    }
    override func draggingUpdated(_ s: NSDraggingInfo) -> NSDragOperation { .copy }
    override func prepareForDragOperation(_ s: NSDraggingInfo) -> Bool { true }
    override func performDragOperation(_ s: NSDraggingInfo) -> Bool {
        despejar(s.draggingPasteboard, "janela: SOLTOU (recusado de propósito)")
        return false
    }
    override func draw(_ r: NSRect) {
        NSColor(calibratedRed: 0.15, green: 0.2, blue: 0.3, alpha: 1).setFill(); r.fill()
        let a: [NSAttributedString.Key: Any] = [.foregroundColor: NSColor.white, .font: NSFont.systemFont(ofSize: 22, weight: .bold)]
        ("SONDA ARRASTO\n\(rotulo)\narraste para cá" as NSString).draw(at: NSPoint(x: 30, y: 60), withAttributes: a)
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let x = args.count > 3 ? Double(args[2]) ?? 1400 : 1400
let y = args.count > 3 ? Double(args[3]) ?? 300 : 300
let janela = NSWindow(contentRect: NSRect(x: x, y: y, width: 420, height: 220), styleMask: [.titled], backing: .buffered, defer: false)
janela.title = "SONDA ARRASTO \(rotulo)"
janela.level = .floating                  // fica por cima do NLE durante o gesto
let alvo = Alvo(frame: janela.contentView!.bounds)
var tipos: [NSPasteboard.PasteboardType] = [.fileURL, .URL, .string, .tiff, .png, .pdf, .rtf, .html, .color, .sound,
    .multipleTextSelection, .tabularText, .fileContents, .findPanelSearchOptions, .textFinderOptions]
tipos += ["public.data", "public.item", "public.content", "public.file-url", "public.url", "public.utf8-plain-text",
          "com.apple.pasteboard.promised-file-url", "com.apple.NSFilePromiseItemMetaData", "NSFilenamesPboardType",
          "NSPromiseContentsPboardType", "com.apple.pasteboard.promised-file-content-type",
          // o MC (Qt 6) no Mac: os MIME do Qt viram com.trolltech.anymime.<mime com / → -->  (medido 2026-10-24)
          "com.trolltech.anymime.application--x-dnditemdata", "com.trolltech.anymime.text--x.avid.mc-api-asset-list+json",
          "com.trolltech.anymime.text--x.avid.asset-list-extended+json", "com.trolltech.qt.MimeTypeName"].map { NSPasteboard.PasteboardType($0) }
alvo.registerForDraggedTypes(tipos)
janela.contentView = alvo
janela.makeKeyAndOrderFront(nil)
app.activate(ignoringOtherApps: true)

let pbArrasto = NSPasteboard(name: .drag)
var visto = pbArrasto.changeCount
escrever("== sonda '\(rotulo)' pronta · \(pasta.path) · drag changeCount inicial \(visto)")
Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
    let c = pbArrasto.changeCount
    if c != visto { visto = c; despejar(pbArrasto, "pasteboard de arrasto mudou (sem precisar soltar)") }
}
app.run()
