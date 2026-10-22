import { splitHighlights } from '../ocrSegments';

it('aralıkları sıralı parçalara böler', () => {
  expect(
    splitHighlights('Depakin devam, uykusuzluk', [
      { bas: 15, son: 25, tur: 'belirti' },
      { bas: 0, son: 7, tur: 'ilac' },
    ]),
  ).toEqual([
    { text: 'Depakin', tur: 'ilac' },
    { text: ' devam, ', tur: null },
    { text: 'uykusuzluk', tur: 'belirti' },
  ]);
});

it('vurgu yoksa tek parça', () => {
  expect(splitHighlights('Kontrol', [])).toEqual([{ text: 'Kontrol', tur: null }]);
});

it('çakışan, sınır dışı ve boş aralıkları atlar', () => {
  expect(
    splitHighlights('abcdef', [
      { bas: 0, son: 3, tur: 'ilac' },
      { bas: 2, son: 4, tur: 'belirti' },
      { bas: 5, son: 99, tur: 'belirti' },
      { bas: 4, son: 4, tur: 'ilac' },
    ]),
  ).toEqual([
    { text: 'abc', tur: 'ilac' },
    { text: 'def', tur: null },
  ]);
});

it('boş metin boş liste', () => {
  expect(splitHighlights('', [])).toEqual([]);
});
