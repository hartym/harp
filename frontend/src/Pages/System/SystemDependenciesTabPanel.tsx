import { OnQuerySuccess } from "Components/Utilities/OnQuerySuccess.tsx"
import { useSystemDependenciesQuery } from "Domain/System"
import { Tab } from "mkui/Components/Tabs"

import { SettingsTable } from "./Components"
import { Pane } from "mkui/Components/Pane"

export function SystemDependenciesTabPanel() {
  const query = useSystemDependenciesQuery()
  return (
    <Tab.Panel>
      <OnQuerySuccess query={query}>
        {(query) => {
          return (
            <Pane hasDefaultPadding={false}>
              <SettingsTable settings={query.data} />
            </Pane>
          )
        }}
      </OnQuerySuccess>
    </Tab.Panel>
  )
}
