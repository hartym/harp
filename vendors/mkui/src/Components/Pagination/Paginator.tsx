import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/20/solid"
import { generate } from "@bramus/pagination-sequence"
import { classNames } from "../../Utilities"

export function Paginator({
  last = 50,
  current = 1,
  perPage = 10,
  total = undefined,
  className = undefined,
  setPage = undefined,
}: {
  last?: number
  current?: number
  perPage?: number
  total?: number
  className?: string
  setPage?: (page: number) => void
}) {
  const setPreviousPage = setPage ? () => setPage(Math.max(1, current - 1)) : undefined
  const setNextPage = setPage ? () => setPage(Math.min(last, current + 1)) : undefined
  return (
    <div
      className={classNames("flex items-center justify-between border-gray-200 bg-white px-4 py-3 sm:px-6", className)}
    >
      <div className="flex flex-1 justify-between sm:hidden">
        <a
          href="#"
          className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          onClick={setPreviousPage ?? undefined}
        >
          Previous
        </a>
        <a
          href="#"
          className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          onClick={setNextPage ?? undefined}
        >
          Next
        </a>
      </div>
      <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-gray-700">
            Showing <span className="font-medium">{(current - 1) * perPage + 1}</span> to{" "}
            <span className="font-medium">{current * perPage}</span>
            {total ? (
              <>
                {" "}
                of <span className="font-medium">{total}</span> results
              </>
            ) : (
              ""
            )}
          </p>
        </div>
        <div>
          <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
            <a
              href="#"
              className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
              onClick={setPreviousPage ?? undefined}
            >
              <span className="sr-only">Previous</span>
              <ChevronLeftIcon className="h-5 w-5" aria-hidden="true" />
            </a>
            {/* Current: "z-10 bg-primary-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600",
                Default: "text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-offset-0" */}

            {generate(current, last, 1, 1, "…").map((i) => {
              if (typeof i === "string") {
                return (
                  <span className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-inset ring-gray-300 focus:outline-offset-0">
                    ...
                  </span>
                )
              } else {
                const isCurrent = i === current
                return (
                  <a
                    href="#"
                    aria-current={isCurrent ? "page" : undefined}
                    className={
                      isCurrent
                        ? "relative z-10 inline-flex items-center bg-primary-600 px-4 py-2 text-sm font-semibold text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
                        : "relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
                    }
                    onClick={
                      setPage
                        ? () => {
                            setPage(i)
                          }
                        : undefined
                    }
                  >
                    {i}
                  </a>
                )
              }
            })}

            <a
              href="#"
              className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0"
              onClick={setNextPage ?? undefined}
            >
              <span className="sr-only">Next</span>
              <ChevronRightIcon className="h-5 w-5" aria-hidden="true" />
            </a>
          </nav>
        </div>
      </div>
    </div>
  )
}
