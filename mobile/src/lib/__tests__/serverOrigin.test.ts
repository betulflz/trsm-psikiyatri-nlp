import { sameServer } from '../serverOrigin';

it('aynı sunucu: boşluk, büyük/küçük harf ve sondaki eğik çizgi önemsiz', () => {
  expect(sameServer('http://192.168.1.20:8765', ' HTTP://192.168.1.20:8765/ ')).toBe(true);
});

it('farklı ana makine, port veya şema farklı sunucudur', () => {
  expect(sameServer('http://192.168.1.20:8765', 'http://192.168.1.21:8765')).toBe(false);
  expect(sameServer('http://192.168.1.20:8765', 'http://192.168.1.20:9000')).toBe(false);
  expect(sameServer('http://sunucu.local', 'https://sunucu.local')).toBe(false);
});

it('yol kısmı farkı aynı sunucuyu değiştirmez ama okunamayan adresler eşit sayılmaz', () => {
  expect(sameServer('http://a:1/x', 'http://a:1')).toBe(true);
  expect(sameServer('bozuk', 'bozuk')).toBe(false);
  expect(sameServer('', 'http://a:1')).toBe(false);
});

import { normalizeServerUrl } from '../serverOrigin';

describe('normalizeServerUrl', () => {
  it('şema yoksa http ekler, boşluk ve sondaki eğik çizgiyi atar', () => {
    expect(normalizeServerUrl(' 192.168.1.5:8765 ')).toBe('http://192.168.1.5:8765');
    expect(normalizeServerUrl('http://a.local:1/')).toBe('http://a.local:1');
    expect(normalizeServerUrl('HTTPS://Sunucu.Local')).toBe('https://sunucu.local');
  });

  it('geçersiz adresleri reddeder', () => {
    for (const bad of ['', '   ', 'bozuk adres', 'ftp://x', 'http://', ':8765', 'http://a b']) {
      expect(normalizeServerUrl(bad)).toBeNull();
    }
  });
});
