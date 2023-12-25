import { ArrowRightIcon } from "@heroicons/react/24/outline"
import { ElementType } from "react"
import tw, { styled } from "twin.macro"
import urlJoin from "url-join"

import { Message } from "Models/Transaction"

import { RequestMethodBadge } from "../Utilities/formatters.tsx"

interface RequestHeadingProps {
  as?: ElementType
  endpoint?: string
  request?: Message
}

const StyledRequestHeading = styled.h1`
  ${tw`text-sm font-semibold leading-6 text-gray-900`}
`

export const RequestHeading = ({ as = "h1", endpoint = undefined, request = undefined }: RequestHeadingProps) => {
  const [method, url] = request ? request.summary.split(" ") : ["", ""]
  return (
    <StyledRequestHeading as={as}>
      {request ? (
        <div className="flex items-center">
          {endpoint ? (
            <span className="inline-flex items-center bg-gray-50 px-1 mr-2 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
              {endpoint}
            </span>
          ) : null}
          <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 mr-1">
            <ArrowRightIcon className="h-3 w-3 text-gray-500" aria-hidden="true" />
          </span>
          <RequestMethodBadge method={method} />
          <span className="mx-1">{urlJoin("/", url || "")}</span>
        </div>
      ) : (
        <span className="text-gray-500 text-sm font-normal">n/a</span>
      )}
    </StyledRequestHeading>
  )
}
