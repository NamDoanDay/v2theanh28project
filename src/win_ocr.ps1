[CmdletBinding()]
param(
    [string]$ImagePath
)

Add-Type -AssemblyName System.Drawing
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null

$fullPath = [System.IO.Path]::GetFullPath($ImagePath)
$fileTask = [Windows.Storage.StorageFile]::GetFileFromPathAsync($fullPath)
$file = $fileTask.GetAwaiter().GetResult()

$streamTask = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
$stream = $streamTask.GetAwaiter().GetResult()

$decoderTask = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
$decoder = $decoderTask.GetAwaiter().GetResult()

$bitmapTask = $decoder.GetSoftwareBitmapAsync()
$softwareBitmap = $bitmapTask.GetAwaiter().GetResult()

$lang = [Windows.Globalization.Language]::new("en-US")
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$ocrTask = $engine.RecognizeAsync($softwareBitmap)
$ocrResult = $ocrTask.GetAwaiter().GetResult()

$outputList = @()
foreach ($line in $ocrResult.Lines) {
    foreach ($word in $line.Words) {
        $box = @(
            @($word.BoundingRect.Left, $word.BoundingRect.Top),
            @($word.BoundingRect.Right, $word.BoundingRect.Top),
            @($word.BoundingRect.Right, $word.BoundingRect.Bottom),
            @($word.BoundingRect.Left, $word.BoundingRect.Bottom)
        )
        $outputList += [PSCustomObject]@{
            Text = $word.Text
            Box = $box
            Score = 0.95
        }
    }
}

$outputList | ConvertTo-Json -Compress
