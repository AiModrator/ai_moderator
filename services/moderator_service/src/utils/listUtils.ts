

export function divideList<T>(list: T[]): [T[], T[]] {
  if (list.length <= 1) {
    return [list, []];
  }

  const middleIndex = Math.floor(list.length / 2);
  const firstHalf = list.slice(0, middleIndex);
  const secondHalf = list.slice(middleIndex);

  return [firstHalf, secondHalf];
}