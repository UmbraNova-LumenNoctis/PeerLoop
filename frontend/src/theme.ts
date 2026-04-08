import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react";

const customConfig = defineConfig({
  theme: {
    tokens: {
      colors: {
		text: { value: "#f0f0f0" },
		primary: { value: "#70cd4b" },
		secondary: { value: "#3d474a" },
		variantSecondary: { value: "#26272dff" },
		variantText: { value: "#e5e7eb" },
		danger: { value: "#CD4B4B" },
		error: { value: "#ff9966" }
      },
		fonts: {
			Poppins: { value: "'Poppins', sans-serif" },
			Montserrat: { value: "'Montserrat', sans-serif" }
		}
    }
  },
	globalCss: {
		"html, body": {
			margin: 0,
			padding: 0,
			scrollBehavior: "smooth"
		},
		"*": {
			boxSizing: "border-box"
		},
		"*:focus-visible": {
			outline: "3px solid",
			outlineColor: "primary",
			outlineOffset: "2px"
		},
		"a, button, [role='button'], input, textarea, select": {
			minHeight: "44px"
		},
		".skip-link": {
			position: "fixed",
			top: "12px",
			left: "12px",
			zIndex: 2000,
			px: "4",
			py: "2",
			borderRadius: "md",
			bg: "primary",
			color: "secondary",
			fontFamily: "Poppins",
			fontWeight: "700",
			transform: "translateY(-150%)",
			transition: "transform 0.2s ease"
		},
		".skip-link:focus-visible": {
			transform: "translateY(0)"
		},
		"@media (prefers-reduced-motion: reduce)": {
			"*": {
				animationDuration: "0.01ms !important",
				animationIterationCount: "1 !important",
				transitionDuration: "0.01ms !important",
				scrollBehavior: "auto !important"
			}
		},
		".title-styles": {
			fontFamily: "Poppins",
			color: "text"
		},
		".text-styles": {
			fontFamily: "Montserrat",
			color: "text"
		}
	}
});

export const system = createSystem(defaultConfig, customConfig);