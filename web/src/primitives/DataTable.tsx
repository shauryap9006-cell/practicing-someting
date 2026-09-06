import React from 'react';

export interface TableColumn<T> {
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  align?: 'left' | 'center' | 'right';
  className?: string;
  headerClassName?: string;
  isNumeric?: boolean;
}

export interface DataTableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  keyExtractor: (row: T, index: number) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyMessage = 'No records found',
  className = '',
}: DataTableProps<T>) {
  return (
    <div
      className={`border border-line rounded-[4px] overflow-x-auto bg-surface ${className}`}
    >
      <table className="w-full text-left border-collapse text-[13px]">
        <thead>
          <tr className="bg-raised border-b border-line">
            {columns.map((col, idx) => {
              const alignClass =
                col.align === 'right' || col.isNumeric
                  ? 'text-right'
                  : col.align === 'center'
                  ? 'text-center'
                  : 'text-left';

              return (
                <th
                  key={col.header || idx}
                  className={`px-3.5 py-2.5 font-mono text-[10px] uppercase tracking-wider text-muted font-medium select-none ${alignClass} ${
                    col.headerClassName || ''
                  }`}
                >
                  {col.header}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-line/60">
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center font-mono text-xs text-muted"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => {
              const rowKey = keyExtractor(row, rowIdx);
              const isClickable = Boolean(onRowClick);

              return (
                <tr
                  key={rowKey}
                  onClick={() => onRowClick?.(row)}
                  className={`transition-colors ${
                    isClickable
                      ? 'cursor-pointer hover:bg-raised/40'
                      : 'hover:bg-raised/20'
                  }`}
                >
                  {columns.map((col, colIdx) => {
                    const cellValue =
                      typeof col.accessor === 'function'
                        ? col.accessor(row)
                        : (row[col.accessor] as unknown as React.ReactNode);

                    const alignClass =
                      col.align === 'right' || col.isNumeric
                        ? 'text-right font-mono tabular-nums'
                        : col.align === 'center'
                        ? 'text-center'
                        : 'text-left';

                    return (
                      <td
                        key={colIdx}
                        className={`px-3.5 py-2.5 text-ink ${alignClass} ${
                          col.className || ''
                        }`}
                      >
                        {cellValue}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
