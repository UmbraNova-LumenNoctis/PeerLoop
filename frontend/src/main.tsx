import { Provider } from "@/components/ui/provider"
import { BrowserRouter } from "react-router-dom";
import { createRoot } from 'react-dom/client';
import { StrictMode } from 'react';
import App from './App';

createRoot(document.getElementById('root') as HTMLElement).render(
	<StrictMode>
		<Provider>
			<BrowserRouter>
				<App />
			</BrowserRouter>
		</Provider>
	</StrictMode>
);
