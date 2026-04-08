"use client"

import {
  Toaster as ChakraToaster,
  Portal,
  Spinner,
  Stack,
  Toast,
  createToaster,
} from "@chakra-ui/react"

export const toaster = createToaster({
  placement: "top",
  pauseOnPageIdle: true,
})

export const Toaster = () => {
  return (
    <Portal>
      <ChakraToaster toaster={toaster} insetInline={{ mdDown: "4" }}>
        {(toast) => (
          <Toast.Root
            width={{ base: "calc(100vw - 1rem)", md: "md" }}
            minH="unset"
            overflow="hidden"
            py="2"
            px="3"
            gap="2"
            borderWidth="1px"
            borderColor={toast.type === "success" ? "primary" : toast.type === "error" ? "danger" : "variantSecondary"}
            bg={toast.type === "success" ? "primary" : toast.type === "error" ? "danger" : "secondary"}
            color={toast.type === "success" ? "secondary" : "text"}
            animationDuration="220ms"
            animationTimingFunction="ease-out"
            css={{
              "&[data-state='open']": {
                animationName: "toast-slide-in-top",
              },
              "&[data-state='closed']": {
                animationName: "toast-slide-out-top",
              },
              "& [data-part='progress-track'], & [data-part='progress-range']": {
                display: "none",
              },
              "@keyframes toast-slide-in-top": {
                from: {
                  opacity: 0,
                  transform: "translateY(-18px)",
                },
                to: {
                  opacity: 1,
                  transform: "translateY(0)",
                },
              },
              "@keyframes toast-slide-out-top": {
                from: {
                  opacity: 1,
                  transform: "translateY(0)",
                },
                to: {
                  opacity: 0,
                  transform: "translateY(-18px)",
                },
              },
            }}
          >
            {toast.type === "loading" ? (
              <Spinner size="sm" color="primary" />
            ) : (
              <Toast.Indicator />
            )}
            <Stack gap="0.5" flex="1" maxWidth="100%">
              {toast.title && (
                <Toast.Title fontSize="sm" lineHeight="1.2">
                  {toast.title}
                </Toast.Title>
              )}
              {toast.description && (
                <Toast.Description fontSize="xs" lineHeight="1.35">
                  {toast.description}
                </Toast.Description>
              )}
            </Stack>
            {toast.action && (
              <Toast.ActionTrigger>{toast.action.label}</Toast.ActionTrigger>
            )}
            {toast.closable && <Toast.CloseTrigger />}
          </Toast.Root>
        )}
      </ChakraToaster>
    </Portal>
  )
}
