/**
 * Frontend integration boundary. Replace this function with the real service adapter.
 * No network request or document transmission occurs in this implementation.
 * @param {{text: string, files: File[], onProgress: Function, onPartial: Function}} input
 */
export async function analyzeDocument(input) {
  void input;
  throw new Error('Сервис анализа пока не подключён. Материалы остались в этой вкладке. Вы можете повторить попытку после подключения сервиса или открыть демонстрационный пример.');
}

export const serviceNotice = 'Сервис анализа пока не подключён. Документы остаются в этой вкладке и никуда не отправляются. Работу с результатами можно посмотреть на примере.';
