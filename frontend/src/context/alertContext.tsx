import { createContext, useState } from "react";
import { toaster } from "@/components/ui/toaster";

export const AlertContext = createContext(null);

export const AlertProvider = ({ children }) => {
	const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");

  const showAlert = (status: boolean = false, msg: string) => {
    setIsSuccess(status);
    setMessage(msg);

    toaster.create({
      type: status ? "success" : "error",
      title: status ? "Succès" : "Erreur",
      description: msg,
      duration: status ? 4000 : 8000,
      closable: true,
    });

    setIsOpen(false);
  };

  const closeAlert = () => setIsOpen(false);

  return (
    <AlertContext.Provider value={{ isOpen, isSuccess, message, showAlert, closeAlert }}>
      {children}
    </AlertContext.Provider>
  );
};
