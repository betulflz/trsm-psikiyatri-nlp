import { isValidTcKimlik, maskTcKimlik } from '../tcKimlik';

describe('isValidTcKimlik', () => {
  it('geçerli numarayı kabul eder', () => {
    expect(isValidTcKimlik('10000000146')).toBe(true);
  });
  it.each(['10000000147', '10000000136', '01234567890', '1234', '1000000014a', ''])(
    '%s geçersiz',
    (value) => expect(isValidTcKimlik(value)).toBe(false),
  );
});

describe('maskTcKimlik', () => {
  it('ilk 3 ve son 2 hane görünür', () => {
    expect(maskTcKimlik('10000000146')).toBe('100******46');
  });
  it('11 hane değilse olduğu gibi döner', () => {
    expect(maskTcKimlik('123')).toBe('123');
  });
});
