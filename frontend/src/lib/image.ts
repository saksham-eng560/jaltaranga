export async function compressReportImage(file: File, maxBytes = 1_000_000): Promise<Blob> {
  if (!file.type.startsWith('image/')) throw new Error('Choose an image file.');
  if (typeof createImageBitmap !== 'function') throw new Error('Image compression is not supported in this browser.');
  const bitmap = await createImageBitmap(file);
  try {
    const ratio = Math.min(1, 1280 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * ratio));
    canvas.height = Math.max(1, Math.round(bitmap.height * ratio));
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Image could not be prepared.');
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    let quality = 0.84;
    let blob: Blob | null = null;
    while (quality >= 0.4) {
      blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
      if (blob && blob.size <= maxBytes) return blob;
      quality -= 0.1;
    }
    throw new Error('Image is still over 1 MB after compression. Choose a smaller photo.');
  } finally { bitmap.close(); }
}
