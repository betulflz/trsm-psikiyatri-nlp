import { createReportUpload } from '../ocr';

jest.mock('expo-file-system', () => ({
  File: class {
    name = 'report.jpg';
    type = 'image/jpeg';
    uri: string;
    constructor(uri: string) { this.uri = uri; }
    async bytes() { return new Uint8Array([255, 216, 255]); }
  },
}));

it('fotoğrafı Expo fetch tarafından okunabilen File olarak ekler', async () => {
  const append = jest.spyOn(FormData.prototype, 'append').mockImplementation(() => {});
  try {
    createReportUpload('file:///report.jpg');
    expect(append.mock.calls[0][0]).toBe('foto');
    const file = append.mock.calls[0][1] as unknown as { uri: string; name: string; bytes: () => Promise<Uint8Array> };
    expect(file.uri).toBe('file:///report.jpg');
    expect(file.name).toBe('report.jpg');
    expect(await file.bytes()).toEqual(new Uint8Array([255, 216, 255]));
  } finally {
    append.mockRestore();
  }
});
