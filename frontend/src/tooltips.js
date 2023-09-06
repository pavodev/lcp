import { Tooltip } from "bootstrap";

let tooltips = [];

export function setTooltips(parent=document) {
    removeTooltips();
    const tooltipTriggerList = Array.from(
      parent.querySelectorAll(".tooltips")
    );
    tooltipTriggerList.forEach((tooltipTriggerEl) => {
      let tooltipInstance = new Tooltip(tooltipTriggerEl);
      tooltips.push(tooltipInstance);
    });
}
export function removeTooltips() {
    tooltips.forEach((tooltipInstance) => {
      tooltipInstance.dispose();
    });
    tooltips = [];
}
export function notification(node,text,options) {
  options = {...{placement:'top',show:true},...(options||{})};
  let tooltipInstance = new Tooltip(node, {trigger:'manual',title:text, ...options});
  if (options.show) tooltipInstance.show();
  return tooltipInstance;
}