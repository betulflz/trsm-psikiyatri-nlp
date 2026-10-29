import { ApiError } from '@/api/errors';
import { createReportUpload, readReport } from '../ocr';

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

describe('readReport', () => {
  const noWait = async () => {};

  it('iş bitene kadar durumu sorar ve ilerlemeyi bildirir', async () => {
    const client = {
      upload: jest.fn(async () => ({ is_id: 'a1', durum: 'sirada', motor: 'qwen3.5:9b', sira: 1 })),
      get: jest.fn()
        .mockResolvedValueOnce({ is_id: 'a1', durum: 'okunuyor', motor: 'qwen3.5:9b', gecen_sn: 75 })
        .mockResolvedValueOnce({ is_id: 'a1', durum: 'bitti', motor: 'qwen3.5:9b', metin: 'Sertralin 50 mg' }),
      post: jest.fn(),
    };
    const progress: string[] = [];
    const result = await readReport(client as never, 'file:///r.jpg', (p) => progress.push(p), noWait);
    expect(result).toEqual({ metin: 'Sertralin 50 mg', motor: 'qwen3.5:9b' });
    expect(client.get).toHaveBeenCalledWith('/api/m/rapor/ocr/a1');
    expect(progress).toEqual(['Sırada: önünde 1 sayfa var…', 'Qwen okuyor… 1 dk 15 sn (bir sayfa birkaç dakika sürebilir)']);
  });

  it('tek ağ kesintisinde yeniden dener, sunucu hatasını gösterir', async () => {
    const client = {
      upload: jest.fn(async () => ({ is_id: 'a1', durum: 'okunuyor', motor: 'q' })),
      get: jest.fn()
        .mockRejectedValueOnce(new ApiError('ag', null, 'ağ yok'))
        .mockResolvedValueOnce({ is_id: 'a1', durum: 'hata', motor: 'q', hata: 'Qwen raporu okuyamadı.' }),
      post: jest.fn(),
    };
    await expect(readReport(client as never, 'file:///r.jpg', () => {}, noWait)).rejects.toThrow('Qwen raporu okuyamadı.');
    expect(client.get).toHaveBeenCalledTimes(2);
  });
});
