import { foldTr, matchesQuery } from '../turkishSearch';

describe('foldTr', () => {
  it('İ → i ve I → ı', () => {
    expect(foldTr('İSMAİL IŞIK')).toBe('ismail ışık');
  });
  it('NFD girdiyi NFC yapar', () => {
    expect(foldTr('Ağrı')).toBe('ağrı');
  });
});

describe('matchesQuery', () => {
  it('Türkçe büyük/küçük harf', () => {
    expect(matchesQuery('İsmail Işık', 'ışı')).toBe(true);
    expect(matchesQuery('İsmail Işık', 'ISMA')).toBe(false); // I → ı, "ısma" yok
    expect(matchesQuery('İsmail Işık', 'İSMA')).toBe(true);
  });
  it('aksansız yazımı da bulur', () => {
    expect(matchesQuery('Ayşe Kaya', 'ayse')).toBe(true);
    expect(matchesQuery('Gül Ağrı', 'gul agri')).toBe(true);
  });
  it('boş sorgu her şeyi eşler', () => {
    expect(matchesQuery('Ayşe', '   ')).toBe(true);
  });
});
