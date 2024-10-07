const initializeModal = (id) => {
  const modalElement = document.getElementById(id);
  if (modalElement) {
    const options = {
      placement: "center-center",
      backdrop: "static",
      backdropClasses: "bg-gray-900/50 dark:bg-gray-900/80 fixed inset-0 z-40",
      closable: true,
    };

    const instanceOptions = {
      id: id,
      override: true,
    };

    const modal = new Modal(modalElement, options, instanceOptions);
    modal.show();
  }
};

const closeModal = (id) => {
  const modalElement = document.getElementById(id);
  if (modalElement) {
    const modal = new Modal(modalElement);
    modal.hide();
  }
};
