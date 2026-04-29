import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

export function CommandBar({ isOpen, onClose }: Props) {
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const navigateTo = (path: string) => {
    navigate(path);
    onClose();
  };

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="command-modal">
        <div className="command-header">
          <input 
            type="text" 
            placeholder="Search commands, policies, or traces..." 
            className="command-input"
            autoFocus
          />
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="command-body">
          <p className="command-group-title">Navigation</p>
          <div className="command-item" onClick={() => navigateTo("/overview")}>Go to Overview</div>
          <div className="command-item" onClick={() => navigateTo("/approvals")}>Go to Approvals</div>
          <div className="command-item" onClick={() => navigateTo("/audit")}>Search Audit Explorer</div>
          
          <p className="command-group-title">Quick Actions</p>
          <div className="command-item" onClick={() => navigateTo("/emergency")}>
            <span className="text-danger">Trigger Kill Switch</span>
          </div>
        </div>
      </div>
    </>
  );
}
